#!/usr/bin/env python3
"""Rebuilds the same Google Play upload key from ANDROID_KEYSTORE_PASSWORD every time.

The key is derived deterministically from the secret password, so it never has to be stored
in this public repository. Same password -> same key -> same fingerprint, on every build.
Usage: python make_key.py OUTPUT.p12   (password read from ANDROID_KEYSTORE_PASSWORD)
"""
import datetime as dt
import hashlib
import os
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

pw = os.environ["ANDROID_KEYSTORE_PASSWORD"]
seed = hashlib.pbkdf2_hmac("sha256", pw.encode(), b"dailytwist-play-upload-key-v1", 400_000)


class Stream:
    def __init__(self, s):
        self.s, self.n = s, 0

    def bytes(self, k):
        self.n += 1
        return hashlib.shake_256(self.s + self.n.to_bytes(8, "big")).digest(k)


rng = Stream(seed)
SMALL = [p for p in range(3, 2000, 2) if all(p % d for d in range(3, int(p ** .5) + 1, 2))]


def probable_prime(n):
    if any(n % p == 0 for p in SMALL):
        return False
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for i in range(40):
        a = int.from_bytes(rng.bytes(128), "big") % (n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def prime(bits):
    while True:
        c = int.from_bytes(rng.bytes(bits // 8), "big") | (3 << (bits - 2)) | 1
        if probable_prime(c) and (c - 1) % 65537:
            return c


e = 65537
p, q = prime(1024), prime(1024)
if p < q:
    p, q = q, p
n, phi = p * q, (p - 1) * (q - 1)
d = pow(e, -1, phi)
key = rsa.RSAPrivateNumbers(p, q, d, d % (p - 1), d % (q - 1), pow(q, -1, p), rsa.RSAPublicNumbers(e, n)).private_key()

name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DailyTwist"),
                  x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DailyTwist"),
                  x509.NameAttribute(NameOID.COUNTRY_NAME, "MA")])
cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(int.from_bytes(hashlib.sha256(seed).digest()[:8], "big"))
        .not_valid_before(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
        .not_valid_after(dt.datetime(2076, 1, 1, tzinfo=dt.timezone.utc))
        .sign(key, hashes.SHA256()))
data = pkcs12.serialize_key_and_certificates(b"upload", key, cert, None,
                                             serialization.BestAvailableEncryption(pw.encode()))
open(sys.argv[1], "wb").write(data)
print("SHA256:", ":".join(f"{b:02X}" for b in cert.fingerprint(hashes.SHA256())))
