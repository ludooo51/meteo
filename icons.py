"""Icônes de l'appli (soleil + nuage sur fond bleu) -> site/icon-192.png, icon-512.png. Dépendance : pillow."""
import os
from PIL import Image, ImageDraw

here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")


def icon(n):
    S = n * 4  # sur-échantillonnage pour des bords lisses
    im = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(im)
    for y in range(S):  # dégradé vertical
        t = y / S
        d.line([(0, y), (S, y)], fill=(int(42 + 20 * t), int(120 - 50 * t), int(214 - 60 * t)))
    u = S / 100  # zone utile centrale (icône "maskable" : marge de 20 %)
    d.ellipse([38 * u, 26 * u, 66 * u, 54 * u], fill=(253, 216, 53))
    for cx, cy, r in [(40, 62, 13), (54, 56, 15), (66, 63, 11)]:
        d.ellipse([(cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u], fill=(255, 255, 255))
    d.rectangle([40 * u, 62 * u, 66 * u, 74 * u], fill=(255, 255, 255))
    return im.resize((n, n), Image.LANCZOS)


for n in (192, 512):
    icon(n).save(os.path.join(here, "icon-%d.png" % n))
print("ok")
