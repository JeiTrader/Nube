"""Genera un video con textos azules animados sobre el futuro de la IA y la robótica.

Uso: python3 generar_video.py  ->  futuro_ia_robotica.mp4
Requiere: pillow, numpy, imageio-ffmpeg
"""
import math
import random
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
OUT = "futuro_ia_robotica.mp4"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

AZUL = (40, 150, 255)
AZUL_CLARO = (120, 200, 255)
CIAN = (0, 220, 255)
BG = (4, 8, 20)

# (duración en segundos, título, [líneas])
ESCENAS = [
    (6, "EL FUTURO DE LA IA\nY LA ROBÓTICA", ["Una revolución que ya comenzó"]),
    (6.5, "2026: LA IA YA PIENSA", ["Razona, programa, escribe y crea",
                                   "Aprende en segundos lo que antes tomaba años"]),
    (6.5, "ROBOTS HUMANOIDES", ["En fábricas, hogares y hospitales",
                                "Trabajando 24/7 junto a los humanos"]),
    (6.5, "MEDICINA DEL FUTURO", ["Diagnósticos en segundos",
                                  "Cirugías robóticas de precisión milimétrica"]),
    (6.5, "FINANZAS E INVERSIÓN", ["Algoritmos que analizan mercados sin descanso",
                                   "Datos + disciplina = ventaja competitiva"]),
    (6.5, "EL NUEVO TRABAJO", ["La IA no te reemplazará...",
                               "te reemplazará quien sepa usarla"]),
    (6, "EL FUTURO ES DE QUIENES\nSE PREPARAN HOY", ["Aprende. Adáptate. Lidera."]),
    (7, "CREADO POR\nJEISSON SERRANO", ["Máster en Inteligencia Artificial"]),
]

random.seed(7)
PARTICULAS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0.3, 1.5),
               random.uniform(1, 3)) for _ in range(140)]
NODOS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0, 6.28)) for _ in range(40)]

_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def fondo(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # cuadrícula en perspectiva que avanza
    horizonte = H * 0.62
    for i in range(-20, 21):
        x0 = W / 2 + i * 40
        x1 = W / 2 + i * 260
        d.line([(x0, horizonte), (x1, H)], fill=(10, 35, 80), width=1)
    off = (t * 60) % 60
    k = 0
    while True:
        y = horizonte + ((k * 60 + off) / 600) ** 2 * (H - horizonte) * 1.2
        if y > H:
            break
        d.line([(0, y), (W, y)], fill=(10, 35, 80), width=1)
        k += 1
    # red neuronal: nodos flotando y conexiones
    pts = [(x + 40 * math.sin(t * 0.5 + p), y + 30 * math.cos(t * 0.4 + p)) for x, y, p in NODOS]
    for i, a in enumerate(pts):
        for b in pts[i + 1:]:
            dist = math.hypot(a[0] - b[0], a[1] - b[1])
            if dist < 260:
                c = int(60 * (1 - dist / 260))
                d.line([a, b], fill=(0, c // 2, c + 20), width=1)
    for x, y in pts:
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(30, 110, 220))
    # partículas ascendentes
    for x, y, v, r in PARTICULAS:
        yy = (y - t * v * 40) % H
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=(40, 90, 170))
    return img


def texto_centrado(d, texto, fnt, cy, color, espacio=12):
    lineas = texto.split("\n")
    alturas = [d.textbbox((0, 0), l, font=fnt)[3] for l in lineas]
    total = sum(alturas) + espacio * (len(lineas) - 1)
    y = cy - total / 2
    for l, h in zip(lineas, alturas):
        w = d.textlength(l, font=fnt)
        d.text(((W - w) / 2, y), l, font=fnt, fill=color)
        y += h + espacio


def capa_texto(t_local, dur, titulo, lineas, final):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    salida = ease((t_local - (dur - 0.8)) / 0.8) if not final else 0
    alpha_g = 1 - salida

    # título: aparece con escala/deslizamiento
    a = ease(t_local / 1.0) * alpha_g
    size = 110 if "\n" in titulo else 120
    fnt = font(FONT_BOLD, size)
    dy = (1 - ease(t_local / 1.0)) * 60 - salida * 40
    n_lin = titulo.count("\n") + 1
    cy_t = H * (0.36 if n_lin > 1 else 0.40) + dy
    texto_centrado(d, titulo, fnt, cy_t, AZUL + (int(255 * a),), 18)

    # barra luminosa bajo el título
    bw = ease((t_local - 0.5) / 0.8) * 700 * alpha_g
    by = cy_t + n_lin * size * 0.62 + 30
    d.rectangle([W / 2 - bw / 2, by, W / 2 + bw / 2, by + 5], fill=CIAN + (int(255 * alpha_g),))

    # subtítulos con efecto máquina de escribir
    fsub = font(FONT_BOLD if final else FONT_REG, 64 if final else 54)
    for i, l in enumerate(lineas):
        inicio = 1.2 + i * 1.3
        n = int(max(0, (t_local - inicio)) * 35)
        vis = l[:n]
        if not vis:
            continue
        y = by + 70 + i * 90
        w = d.textlength(l, font=fsub)
        x = (W - w) / 2
        col = (AZUL_CLARO if not final else CIAN) + (int(255 * alpha_g),)
        d.text((x, y), vis, font=fsub, fill=col)
        if n < len(l) and int(t_local * 4) % 2 == 0:
            cx = x + d.textlength(vis, font=fsub) + 6
            d.rectangle([cx, y + 8, cx + 24, y + 62], fill=CIAN + (int(255 * alpha_g),))
    return capa


def componer(t, capa):
    base = fondo(t).convert("RGBA")
    # resplandor (glow) azul: desenfoque a baja resolución para velocidad
    peq = capa.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    glow = peq.resize((W, H), Image.BILINEAR)
    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, glow)
    base = Image.alpha_composite(base, capa)
    return base.convert("RGB")


def main():
    total = sum(e[0] for e in ESCENAS)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n_frames = int(total * FPS)
    for f in range(n_frames):
        t = f / FPS
        acc = 0
        for i, (dur, titulo, lineas) in enumerate(ESCENAS):
            if t < acc + dur:
                break
            acc += dur
        final = i == len(ESCENAS) - 1
        frame = componer(t, capa_texto(t - acc, dur, titulo, lineas, final))
        if t < 0.6:  # fundido de entrada
            frame = Image.blend(Image.new("RGB", (W, H)), frame, t / 0.6)
        proc.stdin.write(np.asarray(frame).tobytes())
        if f % 150 == 0:
            print(f"{f}/{n_frames}")
    proc.stdin.close()
    proc.wait()
    print("Listo:", OUT)


if __name__ == "__main__":
    main()
