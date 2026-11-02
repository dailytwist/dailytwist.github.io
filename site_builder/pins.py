"""Pinterest: one tall image per recent English article + a feed Pinterest can auto-publish from.

Writes public/pins/<slug>.jpg (1000x1500) and public/pinterest.xml (RSS with images).
Skips quietly if Pillow is missing, so the site build never fails because of it.
"""
import datetime as dt
import hashlib
from pathlib import Path
from xml.sax.saxutils import escape as e

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
W, H = 1000, 1500

# (top colour, bottom colour) per category; picked so white text stays readable
PALETTES = {
    "Entertainment": [("#5b2a86", "#c0398c"), ("#3a1c71", "#d76d77")],
    "Sports": [("#0f3d3e", "#1f8a70"), ("#123a6b", "#2a7de1")],
    "Science": [("#0b2545", "#13315c"), ("#1d3557", "#457b9d")],
    "Lifestyle": [("#7a3e65", "#d4836b"), ("#6d2e46", "#a26769")],
    "Tech": [("#111827", "#374151"), ("#1e1b4b", "#4338ca")],
    "Animals": [("#2d4a22", "#6a8d3a"), ("#3b5d3a", "#8a9a5b")],
    "History": [("#4a2c1a", "#9c6b3c"), ("#3d2b1f", "#7f5539")],
    "Food": [("#7c2d12", "#ea580c"), ("#713f12", "#ca8a04")],
}
DEFAULT = [("#1f2937", "#6b21a8")]


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _wrap(draw, text, font, width):
    lines, cur = [], ""
    for word in text.split():
        t = f"{cur} {word}".strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def make_pin(article, path, domain):
    from PIL import Image, ImageDraw, ImageFont

    pals = PALETTES.get(article.get("category"), DEFAULT)
    top, bot = pals[int(hashlib.md5(article["slug"].encode()).hexdigest(), 16) % len(pals)]
    t, b = _hex(top), _hex(bot)
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        k = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(int(t[i] + (b[i] - t[i]) * k) for i in range(3)))
    d = ImageDraw.Draw(img)
    # soft decorative circles
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    od.ellipse((-260, -220, 520, 560), fill=(255, 255, 255, 22))
    od.ellipse((560, 1080, 1260, 1780), fill=(255, 255, 255, 18))
    img.paste(over, (0, 0), over)
    d = ImageDraw.Draw(img)

    bold = str(FONTS / "Inter-Bold.otf")
    semi = str(FONTS / "Inter-SemiBold.otf")
    cat = (article.get("category") or "Did you know").upper()
    f_cat = ImageFont.truetype(semi, 34)
    cw = d.textlength(cat, font=f_cat)
    d.rounded_rectangle((80, 150, 80 + cw + 56, 150 + 70), radius=35, fill=(255, 255, 255))
    d.text((108, 163), cat, font=f_cat, fill=_hex(top))

    title = article["title"]
    for size in (92, 84, 76, 68, 60, 54):
        f_t = ImageFont.truetype(bold, size)
        lines = _wrap(d, title, f_t, W - 160)
        if len(lines) * size * 1.18 <= 760:
            break
    y = 300
    for ln in lines:
        d.text((80, y), ln, font=f_t, fill=(255, 255, 255))
        y += int(size * 1.18)

    f_d = ImageFont.truetype(semi, 38)
    desc = _wrap(d, article.get("description", ""), f_d, W - 160)[:4]
    y += 50
    for ln in desc:
        d.text((80, y), ln, font=f_d, fill=(255, 255, 255, 220))
        y += 54

    f_cta = ImageFont.truetype(bold, 40)
    cta = "Read more  →"
    tw = d.textlength(cta, font=f_cta)
    d.rounded_rectangle((80, H - 270, 80 + tw + 80, H - 170), radius=50, fill=(255, 255, 255))
    d.text((120, H - 245), cta, font=f_cta, fill=_hex(top))
    f_dom = ImageFont.truetype(semi, 36)
    d.text((80, H - 120), domain, font=f_dom, fill=(255, 255, 255))
    img.save(path, "JPEG", quality=86, optimize=True, progressive=True)


def build(articles, out, url, site, limit=30):
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("pins: Pillow not installed, skipping Pinterest images")
        return 0
    pdir = out / "pins"
    pdir.mkdir(parents=True, exist_ok=True)
    domain = url.split("://", 1)[-1].replace("www.", "")
    items = []
    for a in articles[:limit]:
        jpg = pdir / f"{a['slug']}.jpg"
        make_pin(a, jpg, domain)
        link = f"{url}/articles/{a['slug']}/"
        img = f"{url}/pins/{a['slug']}.jpg"
        pub = dt.datetime.fromisoformat(a["date"]).replace(hour=6, tzinfo=dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        items.append(
            f"<item><title>{e(a['title'])}</title><link>{e(link)}</link><guid>{e(link)}</guid>"
            f"<pubDate>{pub}</pubDate><description>{e(a['description'])}</description>"
            f'<enclosure url="{e(img)}" length="{jpg.stat().st_size}" type="image/jpeg"/>'
            f'<media:content url="{e(img)}" medium="image" type="image/jpeg" width="{W}" height="{H}"/></item>')
    (out / "pinterest.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>'
        f"<title>{e(site)}</title><link>{e(url)}/</link><description>{e(site)} articles</description>"
        f"<language>en</language>{''.join(items)}</channel></rss>", encoding="utf-8")
    return len(items)
