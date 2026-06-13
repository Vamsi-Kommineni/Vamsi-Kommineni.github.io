#!/usr/bin/env python3
"""Generate static image assets (run locally; requires Pillow).

Outputs to assets/img/ as committed files so the site build (build.py) only
needs Jinja2 + PyYAML. Re-run this only when the source photo or branding
changes:  python3 gen_assets.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SRC_PHOTO = ROOT / "profile.png"
OUT = ROOT / "assets" / "img"
OUT.mkdir(parents=True, exist_ok=True)
TTF_DIR = ROOT / "build_fonts_ttf"

# ---- brand palette -----------------------------------------------------
NAVY = (20, 35, 63)        # --ink
NAVY_DEEP = (13, 22, 38)   # dark bg
PAPER = (243, 245, 249)
TEAL = (14, 124, 115)
TEAL_BRIGHT = (63, 184, 172)
VIOLET = (124, 131, 194)   # knowledge-graph edge motif
MUTED = (154, 167, 186)
WHITE = (255, 255, 255)


def load_font(path, size, wght=None):
    try:
        f = ImageFont.truetype(str(path), size)
        if wght is not None:
            try:
                f.set_variation_by_axes([wght])
            except Exception:
                pass
        return f
    except Exception:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)


def square_crop(im, focus=0.30):
    """Center-crop horizontally, bias toward the top so the face stays framed."""
    w, h = im.size
    s = min(w, h)
    left = (w - s) // 2
    top = int((h - s) * focus)
    return im.crop((left, top, left + s, top + s))


def circular(im, size):
    im = square_crop(im).resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    im.putalpha(mask)
    return im


# ---- 1. responsive avatar ---------------------------------------------
def gen_avatar():
    src = Image.open(SRC_PHOTO).convert("RGB")
    sq = square_crop(src).resize((360, 360), Image.LANCZOS)
    # Plain JPEG only: universally-correct MIME on any static host, no WebP/<picture>
    # fallback trap. Displayed at 150px (sidebar) and 32px (top bar).
    sq.save(OUT / "me.jpg", "JPEG", quality=88, optimize=True, progressive=True)
    print("avatar: me.jpg (360x360)")


# ---- 2. Open Graph social card (1200x630) ------------------------------
def gen_og():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), NAVY_DEEP)
    d = ImageDraw.Draw(img, "RGBA")

    # vertical gradient navy -> slightly lighter
    for y in range(H):
        t = y / H
        c = tuple(int(a + (b - a) * t) for a, b in zip(NAVY_DEEP, NAVY))
        d.line([(0, y), (W, y)], fill=c)

    # knowledge-graph motif (right side, behind photo)
    cx, cy = 940, 315
    nodes = [(cx, cy - 150), (cx + 170, cy - 60), (cx + 150, cy + 120),
             (cx - 150, cy + 130), (cx - 175, cy - 55)]
    for nx, ny in nodes:
        d.line([(cx, cy), (nx, ny)], fill=(*VIOLET, 90), width=2)
    for nx, ny in nodes:
        d.ellipse((nx - 7, ny - 7, nx + 7, ny + 7), fill=(*TEAL_BRIGHT, 150))

    # photo (circular, teal ring)
    ph = 250
    photo = circular(Image.open(SRC_PHOTO).convert("RGB"), ph)
    px, py = cx - ph // 2, cy - ph // 2
    d.ellipse((px - 6, py - 6, px + ph + 6, py + ph + 6), outline=TEAL_BRIGHT, width=4)
    img.paste(photo, (px, py), photo)

    # text block (left)
    f_role = load_font(TTF_DIR / "IBMPlexSans.ttf", 26)
    f_name1 = load_font(TTF_DIR / "SpaceGrotesk.ttf", 74, wght=600)
    f_name2 = load_font(TTF_DIR / "SpaceGrotesk.ttf", 74, wght=600)
    f_sub = load_font(TTF_DIR / "IBMPlexSans.ttf", 30)
    f_url = load_font(TTF_DIR / "IBMPlexSans.ttf", 24)

    x = 80
    d.text((x, 138), "GENAI  /  APPLIED AI ENGINEER", font=f_role, fill=TEAL_BRIGHT)
    d.text((x, 188), "Vamsi Krishna", font=f_name1, fill=WHITE)
    d.text((x, 268), "Kommineni", font=f_name2, fill=WHITE)
    d.text((x, 372), "PhD Researcher · FSU Jena", font=f_sub, fill=(225, 231, 240))
    d.text((x, 412), "Generative AI · Knowledge Graphs · Clinical AI", font=f_sub, fill=MUTED)

    # accent underline + url
    d.line([(x, 500), (x + 92, 500)], fill=TEAL_BRIGHT, width=4)
    d.text((x, 520), "vamsi-kommineni.github.io", font=f_url, fill=MUTED)

    img.save(OUT / "og.png", "PNG", optimize=True)
    print("og: og.png (1200x630)")


# ---- 3. favicons + monogram -------------------------------------------
def monogram(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = max(2, int(size * 0.22))
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=TEAL)
    f = load_font(TTF_DIR / "SpaceGrotesk.ttf", int(size * 0.60), wght=700)
    text = "VK"
    box = d.textbbox((0, 0), text, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(((size - tw) / 2 - box[0], (size - th) / 2 - box[1] - size * 0.02),
           text, font=f, fill=WHITE)
    return img


def gen_favicons():
    # icon-180 = apple-touch-icon; icon-192/512 = web manifest. (favicon.svg is
    # hand-authored in assets/img and not regenerated here.)
    for px in (180, 192, 512):
        monogram(px).save(OUT / f"icon-{px}.png", "PNG", optimize=True)
    ico = monogram(64)
    ico.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("favicons: icon-180/192/512.png, favicon.ico")


if __name__ == "__main__":
    gen_avatar()
    gen_og()
    gen_favicons()
    print("done ->", OUT)
