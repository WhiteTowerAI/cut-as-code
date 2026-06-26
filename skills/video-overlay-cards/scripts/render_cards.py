#!/usr/bin/env python
"""Render each overlay card from overlays.json to a full-frame RGBA PNG (transparent
except the card). Cards are bottom-anchored so they never cover a centered face.
Layout/typography auto-scale to the video's w/h (tuned at a 640x298 reference).

Usage: python render_cards.py overlays.json [--out cards/]
"""
import json, os, argparse
from PIL import Image, ImageDraw, ImageFont

# --- fonts (edit here to change platform / visual identity) ---------------
F = "C:/Windows/Fonts/"
BLACK = F + "ariblk.ttf"     # big titles (Arial Black)
BOLD  = F + "arialbd.ttf"    # kickers
SEMI  = F + "seguisb.ttf"    # sub / second line (Segoe UI Semibold)

# --- palette --------------------------------------------------------------
INK    = (12, 20, 28)        # dark panel / scrim
ACCENT = (38, 202, 168)      # teal accent
WHITE  = (245, 248, 249)
MUTED  = (183, 198, 206)
SHADOW = (0, 0, 0)

REF_W, REF_H = 640.0, 298.0  # reference design size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default="cards")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    W, H = spec["video"]["w"], spec["video"]["h"]
    os.makedirs(a.out, exist_ok=True)

    sx, sy = W / REF_W, H / REF_H            # scale x by width, y/fonts by height
    def fx(v): return int(round(v * sx))
    def fy(v): return int(round(v * sy))
    def font(p, v): return ImageFont.truetype(p, max(8, int(round(v * sy))))

    def tw(d, s, f, track=0):
        if not track:
            return d.textlength(s, font=f)
        return sum(d.textlength(c, font=f) + track for c in s) - track

    def text(d, xy, s, f, fill, track=0, shadow=True, sh=2, sa=160):
        x, y = xy
        if shadow:
            cx = x
            for c in s:
                d.text((cx + fx(sh), y + fy(sh)), c, font=f, fill=SHADOW + (sa,))
                cx += d.textlength(c, font=f) + track
        cx = x
        for c in s:
            d.text((cx, y), c, font=f, fill=fill if len(fill) == 4 else fill + (255,))
            cx += d.textlength(c, font=f) + track

    def scrim(img, top_ref, max_alpha):
        top = fy(top_ref)
        g = Image.new("L", (1, H), 0)
        for y in range(H):
            g.putpixel((0, y), 0 if y <= top else int(max_alpha * ((y - top) / (H - top)) ** 1.3))
        layer = Image.new("RGBA", (W, H), INK + (0,))
        layer.putalpha(g.resize((W, H)))
        return Image.alpha_composite(img, layer)

    def render(e):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        t = e["type"]

        if t == "lowerthird":
            img = scrim(img, 188, 90)
            d = ImageDraw.Draw(img)
            f1, f2 = font(BOLD, 20), font(SEMI, 12)
            x0, pad = fx(24), fx(16)
            w1, w2 = tw(d, e["line1"], f1), tw(d, e["line2"], f2)
            pw = int(max(w1, w2)) + pad * 2 + fx(10)
            y0, y1 = fy(226), fy(278)
            d.rounded_rectangle((x0, y0, x0 + pw, y1), radius=fy(9), fill=INK + (205,))
            d.rectangle((x0, y0 + fy(8), x0 + fx(6), y1 - fy(8)), fill=ACCENT + (255,))
            tx = x0 + pad + fx(8)
            text(d, (tx, y0 + fy(7)), e["line1"], f1, WHITE, shadow=False)
            text(d, (tx, y0 + fy(32)), e["line2"], f2, MUTED, shadow=False)

        elif t == "chapter":
            img = scrim(img, 168, 135)
            d = ImageDraw.Draw(img)
            fk, ft = font(BOLD, 11), font(BLACK, 26)
            x0, ky = fx(28), fy(206)
            text(d, (x0 + fx(2), ky), e.get("kicker", ""), fk, ACCENT, track=fx(3))
            ty = ky + fy(18)
            text(d, (x0, ty), e["title"], ft, WHITE, sh=2, sa=170)
            twid = tw(d, e["title"], ft)
            d.rectangle((x0 + fx(1), ty + fy(36), x0 + fx(1) + min(int(twid), fx(360)), ty + fy(39)),
                        fill=ACCENT + (255,))

        elif t in ("intro", "outro"):
            img = scrim(img, 150, 150)
            d = ImageDraw.Draw(img)
            x0 = fx(30)
            d.rectangle((x0, fy(205), x0 + fx(4), fy(268)), fill=ACCENT + (255,))
            tx = x0 + fx(16)
            if t == "intro":
                text(d, (tx, fy(198)), e.get("kicker", ""), font(BOLD, 11), ACCENT, track=fx(2))
                text(d, (tx, fy(213)), e["title"], font(BLACK, 34), WHITE, sh=2, sa=170)
                text(d, (tx, fy(254)), e.get("sub", ""), font(SEMI, 13), MUTED, shadow=False)
            else:
                text(d, (tx, fy(200)), e["title"], font(BLACK, 30), WHITE, sh=2, sa=170)
                text(d, (tx, fy(238)), e.get("sub", ""), font(SEMI, 14), WHITE, shadow=False)
                text(d, (tx, fy(259)), e.get("small", ""), font(SEMI, 11), MUTED, shadow=False)
        else:
            raise SystemExit(f"unknown card type: {t}")

        p = os.path.join(a.out, e["id"] + ".png")
        img.save(p)
        return p

    for e in spec["elements"]:
        print("rendered", e["id"], "->", os.path.basename(render(e)))
    print("done:", len(spec["elements"]), "cards ->", a.out)


if __name__ == "__main__":
    main()
