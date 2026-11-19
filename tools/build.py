"""Render GTA 6 Cheat Sheet posts from jobs/*.json on GitHub Actions.

Job spec (jobs/<id>.json):
{
  "id": "2026-11-19-am-money-tips",
  "formats": ["carousel", "reel"],          # any of: carousel (1080x1350 JPEGs), reel (1080x1920 MP4)
  "slides": [
    {"art": "Vice_City_13", "kicker": "Money", "headline": "Fastest early cash",
     "lines": ["Line one", "Line two"], "rows": [["Label", "Value"]]}
  ],
  "seconds_per_slide": 2.6
}
"art" = a key from tools/art.json (official Rockstar screenshots) or omitted for the brand gradient.
Outputs go to out/<id>/ and out/<id>/done.json lists public raw URLs.
"""
import json, os, glob, subprocess, urllib.request, io, math, random, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO = os.environ.get("GITHUB_REPOSITORY", "gta6cheatsheett-tech/gta6-cheatsheet-media")
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"
ART = json.load(open("tools/art.json"))
FONT_HEAD = "tools/fonts/Anton-Regular.ttf"
FONT_BODY = "tools/fonts/Montserrat-Bold.ttf"
PINK, CYAN, ORANGE, WHITE, SOFT = (255, 61, 166), (40, 230, 255), (255, 166, 64), (255, 255, 255), (230, 222, 245)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
      "Referer": "https://www.rockstargames.com/VI/media/screenshots"}
_cache = {}


def art_image(key):
    if not key or key not in ART:
        return None
    if key in _cache:
        return _cache[key].copy()
    try:
        req = urllib.request.Request(ART[key] + "?akim=1&imdensity=1&imwidth=1920", headers=UA)
        im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB")
        _cache[key] = im
        return im.copy()
    except Exception as e:
        print("art download failed", key, e)
        return None


def gradient(w, h):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    top, mid, bot = (12, 8, 40), (70, 14, 90), (150, 30, 90)
    for y in range(h):
        t = y / h
        a, b, k = (top, mid, t / 0.6) if t < 0.6 else (mid, bot, (t - 0.6) / 0.4)
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)))
    return im


def cover(im, w, h, zoom=1.0, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height) * zoom
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.BICUBIC)
    x = int((im.width - w) * fx)
    y = int((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))


def font(p, s):
    f = ImageFont.truetype(p, s)
    if "Montserrat" in p:
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    return f


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            out.append(cur)
            cur = wd
    if cur:
        out.append(cur)
    return out


def overlay(w, h, s, page, total, has_art):
    """Transparent RGBA text layer: scrim + headline at bottom (competitor-style), credit, brand."""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # bottom scrim
    scrim = Image.new("L", (1, h))
    for y in range(h):
        t = y / h
        scrim.putpixel((0, y), int(235 * max(0, (t - 0.30) / 0.70) ** 1.1) if has_art else 90)
    lay.paste(Image.new("RGBA", (w, h), (6, 3, 18, 255)), (0, 0), scrim.resize((w, h)))
    # top scrim for brand chip
    top = Image.new("L", (1, h))
    for y in range(h):
        top.putpixel((0, y), int(160 * max(0, 1 - y / (h * 0.16))))
    lay.paste(Image.new("RGBA", (w, h), (6, 3, 18, 255)), (0, 0), top.resize((w, h)))
    d = ImageDraw.Draw(lay)
    m = 70
    hsize = s.get("size", 132 if h > 1500 else 118)
    hf, bf, kf = font(FONT_HEAD, hsize), font(FONT_BODY, 44 if h > 1500 else 40), font(FONT_BODY, 38)
    head = wrap(d, s.get("headline", "").upper(), hf, w - 2 * m)
    lines = []
    for ln in s.get("lines", []):
        lines += wrap(d, ln, bf, w - 2 * m) + [None]
    rows = s.get("rows", [])
    block = (60 if s.get("kicker") else 0) + len(head) * int(hsize * 1.02) + 30 + \
        sum(58 if ln else 16 for ln in lines) + len(rows) * 104
    bottom_pad = 150 if h > 1500 else 120
    y = h - bottom_pad - block
    if s.get("kicker"):
        d.text((m, y), s["kicker"].upper(), font=kf, fill=ORANGE)
        y += 60
    for ln in head:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((m, y), ln, font=hf, fill=PINK + (200,))
        lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(16)))
        d = ImageDraw.Draw(lay)
        d.text((m, y), ln, font=hf, fill=WHITE)
        y += int(hsize * 1.02)
    y += 30
    for ln in lines:
        if ln is None:
            y += 16
            continue
        d.text((m, y), ln, font=bf, fill=WHITE)
        y += 58
    for lab, val in rows:
        d.rounded_rectangle([m, y, w - m, y + 88], radius=20, fill=(14, 8, 34, 225), outline=PINK, width=3)
        d.text((m + 28, y + 44), lab, font=bf, fill=SOFT, anchor="lm")
        d.text((w - m - 28, y + 44), val, font=font(FONT_HEAD, 50), fill=CYAN, anchor="rm")
        y += 104
    # brand chip + page counter
    cf = font(FONT_BODY, 28)
    d.rounded_rectangle([m - 10, 56, m + 330, 108], radius=26, fill=(10, 6, 30, 200), outline=CYAN, width=3)
    d.text((m + 160, 82), "GTA 6 CHEAT SHEET", font=cf, fill=CYAN, anchor="mm")
    if total > 1:
        d.text((w - m, 82), f"{page}/{total}", font=cf, fill=SOFT, anchor="rm")
    foot = "@gta6.cheatsheet · Fan page, not affiliated with Rockstar"
    if has_art:
        foot = "Screenshot: Rockstar Games · @gta6.cheatsheet · Unofficial fan page"
    d.text((w // 2, h - 54), foot, font=font(FONT_BODY, 22), fill=SOFT, anchor="mm")
    return lay


def frame(s, w, h, page, total, zoom=1.0, fx=0.5, fy=0.5):
    art = art_image(s.get("art"))
    bg = cover(art, w, h, zoom, fx, fy) if art else cover(gradient(w, h), w, h, zoom, fx, fy)
    out = bg.convert("RGBA")
    out.alpha_composite(overlay(w, h, s, page, total, art is not None))
    return out.convert("RGB")


def build(job):
    jid = job["id"]
    od = f"out/{jid}"
    os.makedirs(od, exist_ok=True)
    slides = job["slides"]
    n = len(slides)
    result = {"id": jid, "carousel": [], "reel": None}
    if "carousel" in job.get("formats", ["carousel"]):
        for i, s in enumerate(slides, 1):
            p = f"{od}/slide_{i}.jpg"
            frame(s, 1080, 1350, i, n).save(p, "JPEG", quality=90, optimize=True)
            result["carousel"].append(RAW + p)
    if "reel" in job.get("formats", []):
        fps, sec = 30, float(job.get("seconds_per_slide", 2.6))
        nf = int(fps * sec)
        tmp = f"/tmp/{jid}"
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        k = 0
        for i, s in enumerate(slides, 1):
            random.seed(f"{jid}{i}")
            fx0, fx1 = random.choice([(0.35, 0.65), (0.65, 0.35), (0.5, 0.5)])
            art = art_image(s.get("art"))
            base = art if art else gradient(1080, 1920)
            lay = overlay(1080, 1920, s, i, 1, art is not None)
            for f in range(nf):
                t = f / max(nf - 1, 1)
                bg = cover(base, 1080, 1920, 1.08 + 0.10 * t, fx0 + (fx1 - fx0) * t, 0.5).convert("RGBA")
                # text slides up + fades in over first 0.35s
                a = min(1, f / (fps * 0.35))
                shift = int(40 * (1 - a))
                L = lay.copy()
                if a < 1:
                    L.putalpha(L.getchannel("A").point(lambda v: int(v * a)))
                bg.alpha_composite(L.crop((0, 0, 1080, 1920 - shift)), (0, shift))
                bg.convert("RGB").save(f"{tmp}/f{k:05d}.jpg", quality=90)
                k += 1
        p = f"{od}/reel.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{tmp}/f%05d.jpg",
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", p], check=True)
        # cover image for the reel
        frame(slides[0], 1080, 1920, 1, 1).save(f"{od}/reel_cover.jpg", "JPEG", quality=90)
        result["reel"] = RAW + p
        result["reel_cover"] = RAW + f"{od}/reel_cover.jpg"
    json.dump(result, open(f"{od}/done.json", "w"), indent=2)
    print("built", jid)


if __name__ == "__main__":
    for jf in sorted(glob.glob("jobs/*.json")):
        job = json.load(open(jf))
        if not os.path.exists(f"out/{job['id']}/done.json"):
            try:
                build(job)
            except Exception as e:
                os.makedirs(f"out/{job['id']}", exist_ok=True)
                json.dump({"id": job["id"], "error": str(e)}, open(f"out/{job['id']}/done.json", "w"))
                print("FAILED", job["id"], e)
