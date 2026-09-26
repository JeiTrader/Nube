"""Película cinematográfica: La Pasión (la crucifixión de Jesús).

Imágenes generadas con IA + movimiento de cámara, gradación de color, grano de
película, partículas, relámpagos, rayos de luz, subtítulos, narración y banda
sonora generada por código. Full HD 1920x1080, formato de cine 2.39:1.

Uso:  python3 generar_pelicula.py  ->  la_pasion.mp4
Requiere: pillow numpy soundfile kokoro-onnx imageio-ffmpeg
Voz Kokoro: variable KOKORO_DIR con kokoro-v1.0.onnx y voices-v1.0.bin
(https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0).
"""
import math
import os
import random
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(AQUI, "recursos")
KOKORO_DIR = os.environ.get("KOKORO_DIR", REC)
OUT = os.path.join(AQUI, "la_pasion.mp4")
TMP_WAV = os.path.join(AQUI, "_audio.wav")

W, H, FPS, SR = 1920, 1080, 30, 24000
BARRA = 138  # barras negras 2.39:1
F_TITULO = os.path.join(REC, "Cinzel.ttf")
F_SUB = os.path.join(REC, "Lora.ttf")
ORO = (222, 184, 90)
VOZ = "em_alex"
FUNDIDO = 1.2

# camara: (zoom inicial, zoom final, centro inicial, centro final) en coords normalizadas
ESCENAS = [
    dict(img="01_jerusalen.jpg", cam=(1.0, 1.12, (0.45, 0.5), (0.55, 0.48)), tono="calido", fx=["polvo"],
         voz=["Jerusalén. Año treinta y tres.",
              "Una ciudad que estaba a punto de presenciar el acontecimiento que cambiaría la historia de la humanidad."]),
    dict(img="02_cena.jpg", cam=(1.0, 1.18, (0.5, 0.5), (0.5, 0.42)), tono="calido", fx=["polvo"],
         voz=["En la última cena, Jesús partió el pan con sus discípulos.",
              "Sabía lo que venía. Y aun así, eligió amar hasta el final."]),
    dict(img="03_getsemani.jpg", cam=(1.05, 1.22, (0.5, 0.5), (0.56, 0.55)), tono="frio", fx=["polvo"],
         voz=["En el huerto de Getsemaní, oró en la oscuridad.",
              "Padre, no se haga mi voluntad, sino la tuya."]),
    dict(img="04_arresto.jpg", cam=(1.15, 1.15, (0.4, 0.5), (0.6, 0.5)), tono="noche", fx=["brasas"],
         voz=["Esa misma noche, soldados con antorchas llegaron a arrestarlo.",
              "Uno de los suyos lo había traicionado."]),
    dict(img="05_pilato.jpg", cam=(1.2, 1.0, (0.5, 0.45), (0.5, 0.5)), tono="neutro", fx=["polvo"],
         voz=["Ante Poncio Pilato, la multitud gritó: ¡crucifícale!",
              "Y el gobernador, lavándose las manos, lo entregó."]),
    dict(img="06_espinas.jpg", cam=(1.0, 1.15, (0.5, 0.45), (0.5, 0.38)), tono="drama", fx=[],
         voz=["Le pusieron una corona de espinas y se burlaron de él.",
              "Pero él no respondió con odio."]),
    dict(img="07_cruz.jpg", cam=(1.1, 1.22, (0.45, 0.5), (0.52, 0.45)), tono="calido", fx=["polvo"],
         voz=["Cargando su cruz por las calles de Jerusalén, cayó... y se levantó.",
              "Cada paso era una decisión de amor."]),
    dict(img="08_golgota.jpg", cam=(1.0, 1.2, (0.5, 0.5), (0.62, 0.45)), tono="tormenta", fx=["polvo"],
         voz=["En el Gólgota, lo crucificaron entre dos ladrones.",
              "Y desde la cruz dijo: Padre, perdónalos, porque no saben lo que hacen."]),
    dict(img="09_maria.jpg", cam=(1.0, 1.16, (0.5, 0.5), (0.42, 0.45)), tono="drama", fx=[],
         voz=["Al pie de la cruz, su madre María lloraba en silencio."]),
    dict(img="10_tinieblas.jpg", cam=(1.0, 1.35, (0.5, 0.5), (0.48, 0.58)), tono="tormenta", fx=["rayos"],
         voz=["Al mediodía, la tierra se cubrió de tinieblas.",
              "Jesús exclamó: Consumado es. Y entregó su espíritu."]),
    dict(img="11_sepulcro.jpg", cam=(1.12, 1.12, (0.58, 0.5), (0.45, 0.5)), tono="frio", fx=[],
         voz=["Su cuerpo fue puesto en un sepulcro nuevo.", "Y una gran piedra selló la entrada."]),
    dict(img="08_golgota.jpg", cam=(1.25, 1.0, (0.4, 0.4), (0.5, 0.5)), tono="gloria",
         fx=["luz", "polvo"], mayor=True, centro_luz=(0.33, 0.28),
         voz=["Pero al tercer día, al amanecer...",
              "la luz venció a las tinieblas. El sepulcro estaba vacío.", "¡Ha resucitado!"]),
]
CREDITO = "Esta película fue creada por Yéison Serrano, máster en inteligencia artificial."

_fuentes = {}


def fuente(ruta, size, var=None):
    k = (ruta, size, var)
    if k not in _fuentes:
        f = ImageFont.truetype(ruta, size)
        if var:
            f.set_variation_by_name(var)
        _fuentes[k] = f
    return _fuentes[k]


# --------------------------------------------------------------------------
# Imagen
# --------------------------------------------------------------------------
TONOS = {  # (mult sombras RGB, mult luces RGB, saturación, contraste, brillo)
    "calido": ((0.9, 0.95, 1.05), (1.08, 1.0, 0.86), 1.05, 1.12, 1.0),
    "frio": ((0.85, 0.95, 1.12), (0.95, 1.0, 1.08), 0.85, 1.1, 0.92),
    "noche": ((0.8, 0.9, 1.15), (1.12, 0.98, 0.8), 1.0, 1.18, 0.95),
    "neutro": ((0.92, 0.97, 1.05), (1.06, 1.0, 0.9), 0.9, 1.1, 1.0),
    "drama": ((0.9, 0.93, 1.02), (1.05, 0.98, 0.9), 0.8, 1.2, 0.95),
    "tormenta": ((0.85, 0.92, 1.1), (1.0, 0.98, 0.95), 0.7, 1.25, 0.9),
    "gloria": ((0.95, 0.95, 1.0), (1.12, 1.04, 0.85), 1.05, 1.05, 1.08),
}


def graduar(img, tono):
    s_mul, l_mul, sat, con, bri = TONOS[tono]
    a = np.asarray(img, dtype=np.float32) / 255.0
    lum = (a * [0.299, 0.587, 0.114]).sum(axis=2, keepdims=True)
    a = lum + (a - lum) * sat
    a = (a - 0.5) * con + 0.5
    a = a * bri
    w = np.clip(lum, 0, 1)
    a = a * (np.array(s_mul) * (1 - w) + np.array(l_mul) * w)
    a = np.clip(a, 0, 1)
    a = a * a * (3 - 2 * a) * 0.35 + a * 0.65  # curva S suave
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def viñeta():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = np.clip(1.08 - 0.45 * r ** 2.2, 0.35, 1.0)
    v8 = (v * 255).astype(np.uint8)
    return Image.merge("RGB", [Image.fromarray(v8)] * 3)


def granos(n=8):
    rnd = np.random.default_rng(5)
    out = []
    for _ in range(n):
        g = rnd.normal(128, 9, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
        gi = Image.fromarray(g).resize((W, H), Image.BILINEAR)
        out.append(Image.merge("RGB", [gi] * 3))
    return out


class Particulas:
    def __init__(self, tipo, semilla):
        rnd = random.Random(semilla)
        self.tipo = tipo
        n = 70 if tipo == "polvo" else 90
        self.p = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.3, 1.0), rnd.uniform(0, 6.28),
                   rnd.uniform(1.2, 3.8)) for _ in range(n)]

    def dibujar(self, capa, t):
        d = ImageDraw.Draw(capa)
        for x, y, v, fase, r in self.p:
            if self.tipo == "polvo":
                xx = (x + t * 14 * v + 25 * math.sin(t * 0.4 + fase)) % W
                yy = (y - t * 6 * v + 18 * math.cos(t * 0.3 + fase)) % H
                a = int(70 + 60 * math.sin(t * 0.8 + fase))
                col = (255, 240, 210, max(0, a))
            else:  # brasas
                xx = (x + 30 * math.sin(t * 1.3 + fase)) % W
                yy = (y - t * 90 * v) % H
                a = int(150 + 100 * math.sin(t * 5 + fase))
                col = (255, int(140 + 60 * v), 40, max(0, min(255, a)))
                r *= 0.8
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=col)


def rayos_luz(t, centro=(0.5, 0.45)):
    """Rayos de luz divina que salen del punto central (capa aditiva)."""
    w4, h4 = W // 4, H // 4
    capa = Image.new("L", (w4, h4), 0)
    d = ImageDraw.Draw(capa)
    cx, cy = centro[0] * w4, centro[1] * h4
    L = 700
    for i in range(18):
        ang = i * 2 * math.pi / 18 + 0.04 * math.sin(t * 0.4 + i)
        a1, a2 = ang - 0.055, ang + 0.055
        d.polygon([(cx, cy), (cx + L * math.cos(a1), cy + L * math.sin(a1)),
                   (cx + L * math.cos(a2), cy + L * math.sin(a2))],
                  fill=int(38 + 22 * math.sin(t * 0.7 + i * 1.7)))
    d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=90)
    capa = capa.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)
    return Image.merge("RGB", [capa, capa.point(lambda v: int(v * 0.85)), capa.point(lambda v: int(v * 0.55))])


def sombra_texto(texto, f, color, sombra=6, ancho=None):
    """Texto (una o varias líneas centradas) con sombra suave."""
    lineas = [texto]
    if ancho:
        lineas, act = [], ""
        for p in texto.split():
            prueba = (act + " " + p).strip()
            if f.getlength(prueba) <= ancho:
                act = prueba
            else:
                lineas.append(act)
                act = p
        lineas.append(act)
    alto = int(f.size * 1.25)
    w = int(max(f.getlength(l) for l in lineas)) + 40
    h = alto * len(lineas) + 40
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ds, di = ImageDraw.Draw(s), ImageDraw.Draw(img)
    for k, l in enumerate(lineas):
        x = (w - f.getlength(l)) / 2
        ds.text((x, 20 + k * alto), l, font=f, fill=(0, 0, 0, 220))
    img.alpha_composite(s.filter(ImageFilter.GaussianBlur(sombra)))
    for k, l in enumerate(lineas):
        x = (w - f.getlength(l)) / 2
        di.text((x, 20 + k * alto), l, font=f, fill=color)
    return img


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------


def narrar():
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin"))

    def tts(txt):
        s, _ = k.create(txt, voice=VOZ, speed=0.88, lang="es")
        s = np.asarray(s, dtype=np.float32)
        return s / (np.max(np.abs(s)) + 1e-9) * 0.9

    escenas = [[tts(f) for f in esc["voz"]] for esc in ESCENAS]
    return escenas, tts(CREDITO)


def reverb(x, seg=2.8, mezcla=0.35):
    n = int(seg * SR)
    rnd = np.random.default_rng(9)
    ir = rnd.standard_normal(n) * np.exp(-np.arange(n) / (SR * seg / 6))
    ir /= np.sqrt((ir ** 2).sum())
    N = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:len(x)]
    y *= np.max(np.abs(x)) / (np.max(np.abs(y)) + 1e-9)
    return x * (1 - mezcla) + y * mezcla


def pasa_bajos(x, k):
    c = np.cumsum(np.insert(x, 0, 0))
    y = (c[k:] - c[:-k]) / k
    return np.pad(y, (k - 1, 0))


def banda_sonora(total, inicio_mayor, golpes, truenos):
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    # drone grave en Re
    for h, a in [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12)]:
        out += a * np.sin(2 * np.pi * 73.42 * h * t + h) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.07 * t))
    out *= 0.18
    # cuerdas: progresión menor y luego mayor en la resurrección
    menor = [[146.83, 174.61, 220.0], [116.54, 146.83, 174.61], [98.0, 146.83, 196.0], [110.0, 138.59, 164.81]]
    mayor = [[146.83, 185.0, 220.0], [196.0, 246.94, 293.66], [110.0, 138.59, 164.81], [146.83, 185.0, 220.0]]
    da = 7.0
    for i in range(int(total / da) + 1):
        a0, a1 = int(i * da * SR), min(n, int((i + 1) * da * SR + 2 * SR))
        if a0 >= n:
            break
        tt = t[a0:a1] - t[a0]
        env = np.minimum(1, tt / 2.5) * np.clip((da + 2 - tt) / 2.5, 0, 1)
        acorde = (mayor if i * da >= inicio_mayor else menor)[i % 4]
        seg = np.zeros(a1 - a0)
        for f in acorde:
            for det in (0.996, 1.0, 1.004):
                ph = 2 * np.pi * f * det * tt
                for h in range(1, 7):  # sierra suavizada
                    seg += np.sin(ph * h) / h * (0.8 ** h)
            # "coro": octava superior suave
            seg += 0.6 * np.sin(4 * np.pi * f * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * 5 * tt) * 0.1)
        out[a0:a1] += pasa_bajos(seg, 12) * env * 0.09
    # golpes de timbal
    for g in golpes:
        a0 = int(g * SR)
        L = min(n - a0, int(3 * SR))
        if L <= 0:
            continue
        tt = np.arange(L) / SR
        f = 55 * np.exp(-tt * 1.5) + 38
        out[a0:a0 + L] += (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2)) * 0.9
    out = reverb(out, 3.2, 0.45)
    # viento
    rnd = np.random.default_rng(2)
    viento = pasa_bajos(rnd.standard_normal(n), 60)
    viento *= (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t + 1)) * 0.25 / (np.max(np.abs(viento)) + 1e-9)
    out += viento
    # truenos
    for tr in truenos:
        a0 = int(tr * SR)
        L = min(n - a0, int(4 * SR))
        if L <= 0:
            continue
        tt = np.arange(L) / SR
        ruido = pasa_bajos(rnd.standard_normal(L), 30)
        ruido /= np.max(np.abs(ruido)) + 1e-9
        env = np.minimum(1, tt / 0.03) * np.exp(-tt * 1.3) * (1 + 0.5 * np.sin(tt * 23))
        out[a0:a0 + L] += ruido * env * 1.2
    out /= np.max(np.abs(out)) + 1e-9
    fade = np.minimum(1, np.minimum(t / 2.0, (total - t) / 4.0))
    return out * fade


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def cargar(esc):
    img = Image.open(os.path.join(REC, esc["img"])).convert("RGB").resize((2560, 1440), Image.LANCZOS)
    return graduar(img, esc["tono"])


def encuadre(img, cam, u):
    z0, z1, c0, c1 = cam
    e = u * u * (3 - 2 * u) * 0.3 + u * 0.7  # casi lineal, con arranque/parada suaves
    z = z0 + (z1 - z0) * e
    cx = c0[0] + (c1[0] - c0[0]) * e
    cy = c0[1] + (c1[1] - c0[1]) * e
    iw, ih = img.size
    cw, ch = iw / z, ih / z
    x0 = min(max(0, cx * iw - cw / 2), iw - cw)
    y0 = min(max(0, cy * ih - ch / 2), ih - ch)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def main():
    print("Narración...", flush=True)
    frases, credito = narrar()

    # línea de tiempo
    INTRO = 6.0
    plan = []  # (esc, inicio, dur, [(t_frase, dur_frase, texto)])
    t = INTRO - FUNDIDO
    for esc, clips in zip(ESCENAS, frases):
        subs, tt = [], 0.8
        for txt, c in zip(esc["voz"], clips):
            subs.append((tt, len(c) / SR, txt))
            tt += len(c) / SR + 0.45
        dur = max(7.0, tt + 1.2)
        plan.append((esc, t, dur, subs))
        t += dur - FUNDIDO
    inicio_creditos = t
    dur_creditos = 3.0 + len(credito) / SR + 3.0
    total = inicio_creditos + dur_creditos
    print(f"Duración: {total:.1f}s", flush=True)

    # audio
    voz = np.zeros(int(total * SR) + SR)
    for esc, t0, dur, subs in plan:
        for (ts, d, _), c in zip(subs, frases[ESCENAS.index(esc)]):
            a = int((t0 + ts) * SR)
            voz[a:a + len(c)] += c
    a = int((inicio_creditos + 2.0) * SR)
    voz[a:a + len(credito)] += credito
    voz = reverb(voz, 1.2, 0.12)
    golpes = [0.8] + [t0 + 0.2 for _, t0, _, _ in plan] + [inicio_creditos + 0.5]
    i10 = [i for i, (e, _, _, _) in enumerate(plan) if "rayos" in e["fx"]][0]
    t10 = plan[i10][1]
    truenos = [t10 + 1.2, t10 + 4.6]
    i_may = [i for i, (e, _, _, _) in enumerate(plan) if e.get("mayor")][0]
    musica = banda_sonora(len(voz) / SR, plan[i_may][1], golpes, truenos)
    env_voz = np.convolve(np.abs(voz), np.ones(4800) / 4800, mode="same")
    duck = 1 - 0.45 * np.clip(env_voz * 8, 0, 1)
    mezcla = voz * 0.95 + musica * 0.33 * duck
    mezcla /= max(1.0, np.max(np.abs(mezcla)) / 0.98)
    sf.write(TMP_WAV, mezcla.astype(np.float32), SR)

    # recursos visuales
    vig = viñeta()
    grano = granos()
    barras = Image.new("L", (W, H), 0)
    ImageDraw.Draw(barras).rectangle([0, BARRA, W, H - BARRA], fill=255)
    negro = Image.new("RGB", (W, H), (0, 0, 0))
    f_sub = fuente(F_SUB, 38, b"Medium")
    cache = {}

    def imagen(esc):
        clave = (esc["img"], esc["tono"])
        if clave not in cache:
            if len(cache) > 2:
                cache.clear()
            cache[clave] = cargar(esc)
        return cache[clave]

    parts = {i: [Particulas(fx, i) for fx in e["fx"] if fx in ("polvo", "brasas")] for i, e in enumerate(ESCENAS)}
    subs_img = {}

    def cuadro_escena(i, esc, t_local, dur):
        fr = encuadre(imagen(esc), esc["cam"], min(1.0, t_local / dur))
        if "luz" in esc["fx"]:
            fr = ImageChops.add(fr, rayos_luz(t_local, esc.get("centro_luz", (0.5, 0.45))))
        if parts[i]:
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for p in parts[i]:
                p.dibujar(capa, t_local)
            fr = fr.convert("RGBA")
            fr.alpha_composite(capa)
            fr = fr.convert("RGB")
        if "rayos" in esc["fx"]:
            for tr in (1.2, 4.6):
                dt = t_local - tr
                if 0 <= dt < 0.35:
                    k = (1 - dt / 0.35) * (0.85 if dt < 0.07 or 0.14 < dt < 0.2 else 0.35)
                    fr = Image.blend(fr, Image.new("RGB", (W, H), (225, 230, 255)), k)
        return fr

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", TMP_WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-tune", "film",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    # títulos
    t_titulo = sombra_texto("LA PASIÓN", fuente(F_TITULO, 170, b"Bold"), ORO, 10)
    t_sub = sombra_texto("La historia que cambió el mundo", fuente(F_SUB, 50, b"Regular"), (235, 225, 205), 6)
    c1 = sombra_texto("Creado por", fuente(F_SUB, 52, b"Regular"), (230, 220, 200))
    c2 = sombra_texto("JEISSON SERRANO", fuente(F_TITULO, 130, b"Bold"), ORO, 10)
    c3 = sombra_texto("Máster en Inteligencia Artificial", fuente(F_TITULO, 56, b"Regular"), (235, 225, 205))

    def pegar_centrado(fr, img, cy, alfa):
        if alfa <= 0:
            return
        im = img.copy()
        im.putalpha(ImageChops.multiply(im.getchannel("A"), Image.new("L", im.size, int(255 * alfa))))
        fr.alpha_composite(im, (int(W / 2 - im.width / 2), int(cy - im.height / 2)))

    n_total = int(total * FPS)
    rnd_polvo = Particulas("polvo", 99)
    for f in range(n_total):
        t = f / FPS
        activos = [(i, e, t0, d, s) for i, (e, t0, d, s) in enumerate(plan) if t0 <= t < t0 + d]
        if t < INTRO:
            fr = negro.copy().convert("RGBA")
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            rnd_polvo.dibujar(capa, t)
            fr.alpha_composite(capa)
            a = min(1, max(0, (t - 0.8) / 1.5)) * min(1, max(0, (INTRO - FUNDIDO - 0.3 - t) / 0.8))
            pegar_centrado(fr, t_titulo, H / 2 - 40, a)
            pegar_centrado(fr, t_sub, H / 2 + 90, min(1, max(0, (t - 1.8) / 1.5)) * min(1, max(0, (INTRO - FUNDIDO - 0.3 - t) / 0.8)))
            fr = fr.convert("RGB")
            if activos:
                i, e, t0, d, s = activos[0]
                fr = Image.blend(fr, cuadro_escena(i, e, t - t0, d), min(1, (t - t0) / FUNDIDO))
        elif t >= inicio_creditos + FUNDIDO or not activos:
            fr = negro.copy().convert("RGBA")
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            rnd_polvo.dibujar(capa, t)
            fr.alpha_composite(capa)
            tc = t - inicio_creditos
            fin = min(1, max(0, (total - 0.8 - t) / 1.5))
            pegar_centrado(fr, c1, H / 2 - 150, min(1, max(0, (tc - 1.4) / 1.2)) * fin)
            pegar_centrado(fr, c2, H / 2 - 30, min(1, max(0, (tc - 2.0) / 1.5)) * fin)
            pegar_centrado(fr, c3, H / 2 + 110, min(1, max(0, (tc - 3.0) / 1.5)) * fin)
            fr = fr.convert("RGB")
        else:
            i, e, t0, d, s = activos[-1]
            fr = cuadro_escena(i, e, t - t0, d)
            if len(activos) > 1:
                ia, ea, ta, da, sa = activos[0]
                prev = cuadro_escena(ia, ea, t - ta, da)
                u = min(1, (t - t0) / FUNDIDO)
                fr = Image.blend(prev, fr, u * u * (3 - 2 * u))
            elif t > t0 + d - FUNDIDO and t >= inicio_creditos:
                fr = Image.blend(fr, negro, min(1, (t - inicio_creditos) / FUNDIDO))
        # acabado de cine
        fr = ImageChops.multiply(fr, vig)
        fr = ImageChops.overlay(fr, grano[f % len(grano)])
        fr = Image.composite(fr, negro, barras)
        # subtítulos
        for i, e, t0, d, s in activos:
            for ts, dd, txt in s:
                tl = t - t0 - ts
                if -0.2 <= tl < dd + 0.3:
                    if txt not in subs_img:
                        subs_img[txt] = sombra_texto(txt, f_sub, (245, 240, 230), 4, ancho=1500)
                    a = min(1, (tl + 0.2) / 0.3, (dd + 0.3 - tl) / 0.3)
                    frr = fr.convert("RGBA")
                    pegar_centrado(frr, subs_img[txt], H - BARRA / 2 + 4, max(0, a))
                    fr = frr.convert("RGB")
        if t < 1.0:
            fr = Image.blend(negro, fr, t)
        proc.stdin.write(fr.tobytes())
        if f % 300 == 0:
            print(f"{f}/{n_total}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(TMP_WAV)
    print("Listo:", OUT, flush=True)


if __name__ == "__main__":
    main()
