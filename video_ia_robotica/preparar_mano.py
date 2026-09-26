"""Recorta la mano (fondo blanco -> transparente) y alarga el antebrazo.

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

# Alargar el antebrazo repitiendo la franja del borde en la dirección del brazo
al = np.asarray(mano)[..., 3] > 128
c = [np.nonzero(al[:, x])[0].mean() for x in (650, 790)]
pend = (c[1] - c[0]) / 140
grande = Image.new("RGBA", (2600, 2000), (0, 0, 0, 0))
banda = mano.crop((784, 0, 800, 800))
paso = 4
for k in range(400, 0, -1):
    grande.alpha_composite(banda, (784 + paso * k, int(round(paso * k * pend))))
grande.alpha_composite(mano, (0, 0))
grande.crop((0, 0) + grande.getbbox()[2:]).save("recursos/mano_rgba.png")
print("ok", pend)
