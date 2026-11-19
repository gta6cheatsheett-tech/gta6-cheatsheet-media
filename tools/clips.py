"""Official Rockstar video clips -> captioned 9:16 videos.

Sources: official downloads from rockstargames.com/VI/media/videos (tools/videos.json).
index:  python tools/clips.py index   -> index/<src>/scenes.json + index/<src>/sheet_N.jpg (numbered thumbnails)
clip job (jobs/<id>.json): {"id":..., "type":"clip", "source":"Extended_Look", "segments":[{"scene":12} or {"start":31.2,"end":38.0}],
   "hook":"TOP TEXT HOOK", "captions":["line shown during seg 1", "line for seg 2"]}
Output: out/<id>/reel.mp4 (+ reel_cover.jpg, done.json). Original audio is removed (trailer music is licensed).
"""
import json, os, sys, subprocess, urllib.request, glob, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO = os.environ.get("GITHUB_REPOSITORY", "gta6cheatsheett-tech/gta6-cheatsheet-media")
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"
VIDEOS = json.load(open("tools/videos.json"))
CACHE = os.path.expanduser("~/vidcache")
HEAD = "tools/fonts/Anton-Regular.ttf"
BODY = "tools/fonts/Montserrat-Bold.ttf"
PINK, CYAN = (255, 61, 166), (40, 230, 255)


def font(p, s):
    f = ImageFont.truetype(p, s)
    if "Montserrat" in p:
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    return f


def run(cmd):
    print(" ".join(cmd)[:200])
    subprocess.run(cmd, check=True)


def src_path(name):
    os.makedirs(CACHE, exist_ok=True)
    p = f"{CACHE}/{name}.mp4"
    if not os.path.exists(p):
        req = urllib.request.Request(VIDEOS[name], headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.rockstargames.com/VI/media/videos"})
        with urllib.request.urlopen(req, timeout=600) as r, open(p + ".part", "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        os.rename(p + ".part", p)
    return p


def duration(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return float(out.strip())


def index(name):
    od = f"index/{name}"
    if os.path.exists(f"{od}/scenes.json"):
        return
    os.makedirs(od, exist_ok=True)
    p = src_path(name)
    dur = duration(p)
    res = subprocess.run(["ffmpeg", "-hide_banner", "-i", p, "-vf", "scale=480:-2,select='gt(scene,0.32)',showinfo", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    cuts = [0.0]
    for ln in res.splitlines():
        if "pts_time:" in ln:
            t = float(ln.split("pts_time:")[1].split()[0])
            if t - cuts[-1] > 0.8:
                cuts.append(t)
    cuts.append(dur)
    scenes = [{"scene": i + 1, "start": round(a, 2), "end": round(b, 2)} for i, (a, b) in enumerate(zip(cuts, cuts[1:])) if b - a >= 1.0]
    tw, th = 384, 216
    per = 20
    f = font(BODY, 26)
    for si in range(0, len(scenes), per):
        sheet = Image.new("RGB", (tw * 4, (th + 34) * 5), (10, 8, 20))
        d = ImageDraw.Draw(sheet)
        for k, sc in enumerate(scenes[si:si + per]):
            mid = (sc["start"] + sc["end"]) / 2
            tmp = "/tmp/th.jpg"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(mid), "-i", p, "-frames:v", "1", "-vf", f"scale={tw}:{th}", tmp], check=True)
            x, y = (k % 4) * tw, (k // 4) * (th + 34)
            sheet.paste(Image.open(tmp), (x, y))
            d.text((x + 8, y + th + 4), f"#{sc['scene']}  {sc['start']:.1f}-{sc['end']:.1f}s", font=f, fill=(255, 255, 255))
        sheet.save(f"{od}/sheet_{si // per + 1}.jpg", quality=80)
    json.dump({"source": name, "duration": dur, "scenes": scenes}, open(f"{od}/scenes.json", "w"), indent=1)
    print("indexed", name, len(scenes))


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def text_png(path, hook, caption):
    W, H = 1080, 1920
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hf = font(HEAD, 92)
    lines = wrap(d, hook.upper(), hf, W - 140)
    y0 = 300 - len(lines) * 50
    box_h = len(lines) * 100 + 50
    d.rounded_rectangle([50, y0, W - 50, y0 + box_h], radius=28, fill=(255, 255, 255, 245))
    y = y0 + 25
    for ln in lines:
        d.text((W // 2, y), ln, font=hf, fill=(10, 8, 20), anchor="ma")
        y += 100
    if caption:
        cf = font(BODY, 52)
        cy = 1420
        for ln in wrap(d, caption, cf, W - 160):
            tw = d.textlength(ln, font=cf)
            d.rounded_rectangle([W / 2 - tw / 2 - 24, cy - 8, W / 2 + tw / 2 + 24, cy + 66], radius=18, fill=(10, 8, 30, 220))
            d.text((W // 2, cy), ln, font=cf, fill=(255, 255, 255), anchor="ma")
            cy += 82
    d.rounded_rectangle([W // 2 - 190, 1700, W // 2 + 190, 1756], radius=28, fill=(10, 6, 30, 210), outline=CYAN, width=3)
    d.text((W // 2, 1728), "GTA 6 CHEAT SHEET", font=font(BODY, 30), fill=CYAN, anchor="mm")
    d.text((W // 2, 1810), "Footage: Rockstar Games · Unofficial fan page", font=font(BODY, 26), fill=(230, 222, 245), anchor="mm")
    im.save(path)


def clip(job):
    jid = job["id"]
    od = f"out/{jid}"
    os.makedirs(od, exist_ok=True)
    name = job["source"]
    p = src_path(name)
    scenes = {}
    if os.path.exists(f"index/{name}/scenes.json"):
        scenes = {s["scene"]: s for s in json.load(open(f"index/{name}/scenes.json"))["scenes"]}
    parts = []
    caps = job.get("captions", [])
    for i, seg in enumerate(job["segments"]):
        if "scene" in seg:
            sc = scenes[seg["scene"]]
            a, b = sc["start"] + 0.1, sc["end"] - 0.1
        else:
            a, b = seg["start"], seg["end"]
        b = min(b, a + float(seg.get("max", 6)))
        ov = f"/tmp/{jid}_ov{i}.png"
        text_png(ov, job["hook"], caps[i] if i < len(caps) else "")
        part = f"/tmp/{jid}_p{i}.mp4"
        fc = ("[0:v]split=2[bg][fg];"
              "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:2,eq=brightness=-0.12[bgb];"
              "[fg]scale=1080:-2[fgs];"
              "[bgb][fgs]overlay=0:(H-h)/2-40[v0];"
              "[v0][1:v]overlay=0:0,fps=30,format=yuv420p[v]")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(a), "-to", str(b), "-i", p, "-i", ov,
             "-filter_complex", fc, "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", part])
        parts.append(part)
    lst = f"/tmp/{jid}_list.txt"
    open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
    out = f"{od}/reel.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", out])
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.6", "-i", out, "-frames:v", "1", f"{od}/reel_cover.jpg"])
    json.dump({"id": jid, "type": "clip", "carousel": [], "reel": RAW + out, "reel_cover": RAW + f"{od}/reel_cover.jpg",
               "seconds": round(duration(out), 1)}, open(f"{od}/done.json", "w"), indent=2)
    print("clip built", jid)


if __name__ == "__main__":
    if sys.argv[1:] == ["index"]:
        for n in VIDEOS:
            try:
                index(n)
            except Exception as e:
                print("index failed", n, e)
