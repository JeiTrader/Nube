"""Recorta la mano (fondo blanco -> transparente) y difumina el antebrazo.

Uso: python3 preparar_mano.py   (lee recursos/mano.png, escribe recursos/mano_rgba.png)
La punta del marcador queda en PUNTA = (135, 416).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

im = Image.open("recursos/mano.png").convert("RGB")
a = np.asarray(im).astype(np.int16)
blanco = (a.min(axis=2) > 222) & ((a.max(axis=2) - a.min(axis=2)) < 18)
m = Image.fromarray((blanco * 255).astype(np.uint8), "L").copy()
W, H = m.size
for p in [(0, 0), (W - 1, 0), (0, H - 1), (W // 2, 0), (0, H // 2), (W // 2, H - 1)]:
    if m.getpixel(p) == 255:
        ImageDraw.floodfill(m, p, 128)
fondo = np.asarray(m) == 128
A = Image.fromarray(np.where(fondo, 0, 255).astype(np.uint8))
A = A.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.3))
mano = im.convert("RGBA")
mano.putalpha(A)

# Difuminar el antebrazo después de la muñeca (sin brazo largo artificial)
d = np.array([1.0, 0.65]) / np.hypot(1.0, 0.65)
yy, xx = np.mgrid[0:H, 0:W]
proy = xx * d[0] + yy * d[1]
s0 = 590 * d[0] + 430 * d[1]
fade = np.clip(1 - (proy - s0) / 170.0, 0, 1) ** 1.5
alfa = np.asarray(mano.getchannel("A"), dtype=np.float32) * fade
mano.putalpha(Image.fromarray(alfa.astype(np.uint8)))
mano = mano.crop(mano.getbbox()[:2] and (0, 0) + mano.getbbox()[2:])
mano.save("recursos/mano_rgba.png")
print("ok", mano.size)
