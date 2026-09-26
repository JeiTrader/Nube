"""Video estilo pizarra (whiteboard): una mano dibuja bocetos, escribe textos azules
y un narrador explica el futuro de la IA y la robótica.

Uso:  python3 generar_video.py  ->  futuro_ia_robotica.mp4
Requiere: pillow numpy soundfile kokoro-onnx imageio-ffmpeg
Modelo de voz (Kokoro, se descarga de GitHub):
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
Ruta de los modelos: variable de entorno KOKORO_DIR (por defecto ./recursos).
"""
import math
import os
import random
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(AQUI, "recursos")
KOKORO_DIR = os.environ.get("KOKORO_DIR", REC)
OUT = os.path.join(AQUI, "futuro_ia_robotica.mp4")
TMP_WAV = os.path.join(AQUI, "_narracion.wav")

W, H, FPS, SR = 1920, 1080, 30, 24000
SS = 2  # supermuestreo de trazos (antialias)
FONT = os.path.join(REC, "PermanentMarker-Regular.ttf")
VOZ = "em_alex"

PIZARRA = (250, 250, 247)
TINTA = (38, 42, 54)
AZUL = (20, 105, 230)
AZUL_OSC = (10, 70, 170)

SLIDE = 0.6      # transición entre escenas
PAUSA_FIN = 1.0  # silencio al final de cada escena

# --------------------------------------------------------------------------
# Bocetos (coordenadas locales 0..600). Cada trazo: (color, grosor, puntos)
# --------------------------------------------------------------------------


def circulo(cx, cy, r, a0=0, a1=360, n=48):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def cabeza_robot():
    t, a = TINTA, AZUL
    s = [(t, 6, rect(150, 150, 450, 420)),
         (t, 5, [(300, 150), (300, 95)]), (a, 5, circulo(300, 78, 17)),
         (a, 6, circulo(230, 260, 36)), (a, 6, circulo(370, 260, 36)),
         (a, 10, circulo(230, 260, 8, n=12)), (a, 10, circulo(370, 260, 8, n=12)),
         (t, 5, rect(215, 335, 385, 380))]
    for x in (257, 300, 343):
        s.append((t, 4, [(x, 335), (x, 380)]))
    s += [(t, 5, rect(118, 230, 150, 330)), (t, 5, rect(450, 230, 482, 330)),
          (t, 5, rect(262, 420, 338, 465)),
          (t, 6, [(140, 580), (170, 465), (430, 465), (460, 580)]),
          (a, 5, circulo(300, 520, 22))]
    return s


def chip_cerebro():
    t, a = TINTA, AZUL
    s = [(t, 6, rect(190, 190, 410, 410)), (a, 5, rect(240, 240, 360, 360))]
    for i in range(5):
        p = 215 + i * 42.5
        for q in [((p, 190), (p, 120)), ((p, 410), (p, 480)),
                  ((190, p), (120, p)), ((410, p), (480, p))]:
            s.append((t, 4, list(q)))
    for c in [(p, 108) for p in (215, 300, 385)] + [(p, 492) for p in (257.5, 342.5)] + \
             [(108, p) for p in (257.5, 342.5)] + [(492, p) for p in (215, 300, 385)]:
        s.append((a, 4, circulo(c[0], c[1], 11, n=16)))
    # "chispas" de ideas
    for ang in range(0, 360, 45):
        r0, r1 = 250, 290
        s.append((a, 4, [(300 + r0 * math.cos(math.radians(ang)), 300 + r0 * math.sin(math.radians(ang))),
                         (300 + r1 * math.cos(math.radians(ang)), 300 + r1 * math.sin(math.radians(ang)))]))
    s.append((a, 5, [(270, 285), (285, 320), (300, 280), (315, 320), (330, 285)]))
    return s


def robot_humanoide():
    t, a = TINTA, AZUL
    return [(t, 6, rect(245, 30, 355, 130)), (a, 7, [(268, 75), (332, 75)]),
            (t, 5, [(300, 30), (300, 5)]),
            (t, 5, rect(282, 130, 318, 152)),
            (t, 6, rect(200, 152, 400, 350)), (a, 6, circulo(300, 225, 32)),
            (a, 4, [(240, 300), (360, 300)]), (a, 4, [(240, 320), (360, 320)]),
            (t, 6, [(200, 165), (145, 255), (125, 345)]), (t, 5, circulo(120, 365, 20)),
            (t, 6, [(400, 165), (455, 255), (475, 345)]), (t, 5, circulo(480, 365, 20)),
            (t, 6, rect(215, 350, 385, 380)),
            (t, 6, [(250, 380), (240, 520), (205, 570)]), (t, 6, [(205, 570), (265, 570)]),
            (t, 6, [(350, 380), (360, 520), (395, 570)]), (t, 6, [(335, 570), (395, 570)]),
            (a, 4, circulo(245, 450, 10, n=16)), (a, 4, circulo(355, 450, 10, n=16))]


def medicina():
    t, a = TINTA, AZUL
    corazon = []
    for i in range(121):
        u = 2 * math.pi * i / 120
        x = 16 * math.sin(u) ** 3
        y = 13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u)
        corazon.append((300 + x * 14, 250 - y * 14))
    pulso = [(20, 520), (170, 520), (200, 470), (235, 590), (275, 420), (310, 560),
             (335, 520), (580, 520)]
    cruz = [(470, 60), (510, 60), (510, 100), (550, 100), (550, 140), (510, 140),
            (510, 180), (470, 180), (470, 140), (430, 140), (430, 100), (470, 100), (470, 60)]
    return [(t, 7, corazon), (a, 7, pulso), (a, 6, cruz)]


def finanzas():
    t, a = TINTA, AZUL
    s = [(t, 6, [(60, 40), (60, 550), (570, 550)])]
    velas = [(110, 430, 490, 400, 510, True), (175, 460, 400, 380, 480, False),
             (240, 400, 340, 320, 420, True), (305, 350, 380, 330, 400, False),
             (370, 350, 260, 240, 370, True), (435, 270, 200, 170, 290, True),
             (500, 200, 130, 100, 220, True)]
    for x, o, c, hi, lo, sube in velas:
        col = a if sube else t
        s.append((col, 4, [(x, hi), (x, lo)]))
        s.append((col, 5, rect(x - 18, min(o, c), x + 18, max(o, c))))
    s.append((a, 8, [(80, 500), (190, 420), (260, 450), (390, 280), (540, 110)]))
    s.append((a, 8, [(485, 115), (540, 110), (530, 165)]))
    return s


def humano_y_robot():
    t, a = TINTA, AZUL
    return [(t, 6, circulo(160, 170, 45)), (t, 6, [(160, 215), (160, 390)]),
            (t, 6, [(160, 390), (110, 540)]), (t, 6, [(160, 390), (210, 540)]),
            (t, 6, [(160, 260), (95, 350)]), (t, 6, [(160, 260), (285, 320)]),
            (t, 6, rect(390, 110, 490, 205)), (a, 6, circulo(420, 155, 10, n=16)),
            (a, 6, circulo(460, 155, 10, n=16)), (t, 5, [(440, 110), (440, 80)]),
            (t, 6, rect(380, 225, 500, 395)), (t, 6, [(410, 395), (405, 540)]),
            (t, 6, [(470, 395), (475, 540)]), (t, 6, [(500, 260), (550, 350)]),
            (t, 6, [(380, 260), (315, 320)]),
            (a, 6, circulo(300, 322, 30)),
            (a, 5, circulo(300, 322, 70, 200, 340, 20))]


def cohete():
    t, a = TINTA, AZUL
    cuerpo = [(300, 40), (345, 110), (365, 190), (365, 390), (235, 390), (235, 190), (255, 110),
              (300, 40)]
    s = [(t, 7, cuerpo), (a, 6, circulo(300, 215, 38)), (a, 4, circulo(300, 215, 22)),
         (t, 6, [(235, 300), (170, 430), (235, 395)]), (t, 6, [(365, 300), (430, 430), (365, 395)]),
         (a, 6, [(255, 400), (270, 490), (290, 430), (300, 540), (310, 430), (330, 490), (345, 400)]),
         (t, 5, [(300, 390), (300, 330)])]
    for x, y in [(90, 90), (510, 150), (120, 300), (480, 320), (70, 480), (540, 500)]:
        s.append((a, 4, [(x - 14, y), (x + 14, y)]))
        s.append((a, 4, [(x, y - 14), (x, y + 14)]))
    return s


def birrete():
    t, a = TINTA, AZUL
    return [(t, 7, [(300, 100), (560, 200), (300, 300), (40, 200), (300, 100)]),
            (t, 6, [(150, 245), (150, 360)]),
            (t, 6, [(450, 245), (450, 360)]),
            (t, 6, circulo(300, 355, 150, 0, 180, 30)),
            (a, 6, [(300, 200), (520, 250), (520, 380)]),
            (a, 6, circulo(520, 400, 18, n=16))]


# --------------------------------------------------------------------------
# Guion
# --------------------------------------------------------------------------
ESCENAS = [
    dict(titulo="El futuro de la IA y la robótica", boceto=cabeza_robot,
         puntos=["Una revolución", "que ya comenzó"],
         voz="¿Cómo será el mundo en los próximos diez años? La inteligencia artificial "
             "y la robótica lo están cambiando todo. Y lo están haciendo ahora mismo."),
    dict(titulo="La IA ya piensa", boceto=chip_cerebro,
         puntos=["Razona y programa", "Escribe y crea", "Aprende en segundos"],
         voz="Hoy, la inteligencia artificial ya razona, escribe, programa y crea. "
             "Aprende en segundos lo que a una persona le tomaría años."),
    dict(titulo="Robots humanoides", boceto=robot_humanoide,
         puntos=["Fábricas", "Hogares", "Hospitales"],
         voz="Los robots humanoides están saliendo de los laboratorios. Muy pronto los veremos "
             "en fábricas, en hogares y en hospitales, trabajando día y noche junto a nosotros."),
    dict(titulo="Medicina del futuro", boceto=medicina,
         puntos=["Diagnósticos en segundos", "Cirugía robótica precisa"],
         voz="En la medicina, la inteligencia artificial detecta enfermedades antes que el ojo "
             "humano, y los robots realizan cirugías con una precisión milimétrica."),
    dict(titulo="Finanzas e inversión", boceto=finanzas,
         puntos=["Algoritmos 24/7", "Datos + disciplina", "= ventaja"],
         voz="En los mercados financieros, los algoritmos analizan millones de datos por segundo. "
             "La ventaja ya no es la suerte. Es la información, y sobre todo, la disciplina."),
    dict(titulo="El nuevo trabajo", boceto=humano_y_robot,
         puntos=["La IA no te reemplaza...", "te reemplaza quien", "sepa usarla"],
         voz="Muchos trabajos van a cambiar. Pero recuerda esto: la inteligencia artificial "
             "no te va a reemplazar. Te va a reemplazar quien sepa usarla."),
    dict(titulo="El futuro es de quienes se preparan hoy", boceto=cohete,
         puntos=["Aprende", "Adáptate", "Lidera"],
         voz="El futuro no espera a nadie. Pertenece a quienes se preparan hoy. "
             "Aprende. Adáptate. Y lidera."),
    dict(final=True, boceto=birrete,
         voz="Este video fue creado por Yéison Serrano, máster en inteligencia artificial."),
]

# --------------------------------------------------------------------------
# Elementos animables
# --------------------------------------------------------------------------
_fuentes = {}


def fuente(size):
    if size not in _fuentes:
        _fuentes[size] = ImageFont.truetype(FONT, size)
    return _fuentes[size]


def remuestrear(pts, paso=6.0):
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(d / paso))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(1, n + 1)]
    return out


def temblor(pts, amp, rnd):
    """Pequeña ondulación para que el trazo parezca hecho a mano."""
    f1, f2, p1, p2 = rnd.uniform(0.01, 0.03), rnd.uniform(0.01, 0.03), rnd.uniform(0, 6), rnd.uniform(0, 6)
    res, acc = [], 0.0
    for i, (x, y) in enumerate(pts):
        if i:
            acc += math.hypot(x - pts[i - 1][0], y - pts[i - 1][1])
        res.append((x + amp * math.sin(acc * f1 + p1), y + amp * math.sin(acc * f2 + p2)))
    return res


class Boceto:
    """Grupo de trazos que la mano dibuja uno tras otro (con desplazamientos entre trazos)."""

    def __init__(self, trazos, ox, oy, escala, rnd):
        self.segs = []  # (tipo, color, grosor, puntos, longitud)
        prev = None
        for color, grosor, pts in trazos:
            pts = [(ox + x * escala, oy + y * escala) for x, y in pts]
            pts = temblor(remuestrear(pts), 1.6, rnd)
            if prev is not None:
                d = math.hypot(pts[0][0] - prev[0], pts[0][1] - prev[1])
                self.segs.append(("mover", None, 0, [prev, pts[0]], d * 0.35))
            L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
            self.segs.append(("trazo", color, grosor * escala * 1.1, pts, L))
            prev = pts[-1]
        self.total = sum(s[4] for s in self.segs)
        self.dibujado = [0.0] * len(self.segs)  # longitud ya pintada en el lienzo por trazo
        self.peso = self.total / 900.0  # segundos sugeridos

    def avanzar(self, p, lienzo):
        """Pinta hasta la fracción p y devuelve la posición de la punta del marcador."""
        objetivo = p * self.total
        acc = 0.0
        punta = None
        dr = ImageDraw.Draw(lienzo)
        for i, (tipo, color, grosor, pts, L) in enumerate(self.segs):
            if objetivo <= acc:
                break
            local = min(L, objetivo - acc)
            if tipo == "mover":
                f = local / L if L else 1
                a, b = pts
                punta = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            else:
                punta = self._pintar(dr, i, color, grosor, pts, local)
            acc += L
        return punta

    def _pintar(self, dr, i, color, grosor, pts, hasta):
        desde = self.dibujado[i]
        recorrido = 0.0
        punta = pts[0]
        w = max(2, int(grosor * SS))
        for a, b in zip(pts, pts[1:]):
            d = math.hypot(b[0] - a[0], b[1] - a[1])
            if recorrido + d <= desde:
                recorrido += d
                punta = b
                continue
            if recorrido >= hasta:
                break
            f = min(1.0, (hasta - recorrido) / d) if d else 1.0
            fin = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            A = (a[0] * SS, a[1] * SS)
            B = (fin[0] * SS, fin[1] * SS)
            dr.line([A, B], fill=color, width=w)
            r = w / 2
            dr.ellipse([B[0] - r, B[1] - r, B[0] + r, B[1] + r], fill=color)
            punta = fin
            recorrido += d
        self.dibujado[i] = max(desde, hasta)
        return punta


class Texto:
    """Texto azul que se revela de izquierda a derecha, como escrito a mano."""

    def __init__(self, texto, size, cx, y, color=AZUL, punto=False, x=None):
        f = fuente(size)
        bb = f.getbbox(texto)
        extra = int(size * 0.55) if punto else 0
        w, h = bb[2] + extra + 10, bb[3] + int(size * 0.35)
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        if punto:
            r = size * 0.12
            cy = size * 0.62
            d.ellipse([4, cy - r, 4 + 2 * r, cy + r], fill=color)
        d.text((extra, 0), texto, font=f, fill=color)
        self.x = int(cx - w / 2) if x is None else int(x)
        self.y = int(y)
        self.h = h
        self.size = size
        self.peso = 0.35 + 0.055 * len(texto)

    def parcial(self, p):
        w = max(1, int(self.img.width * p))
        return self.img.crop((0, 0, w, self.img.height))

    def punta(self, p, t):
        x = self.x + self.img.width * p
        y = self.y + self.size * (0.55 + 0.25 * math.sin(t * 38))
        return (x, y)


def texto_ajustado(texto, size_max, ancho_max, cx, y, **kw):
    size = size_max
    while fuente(size).getlength(texto) > ancho_max and size > 30:
        size -= 4
    return Texto(texto, size, cx, y, **kw)


# --------------------------------------------------------------------------
# Construcción de escenas
# --------------------------------------------------------------------------


def construir(esc, idx):
    rnd = random.Random(idx * 101 + 7)
    elems = []
    if esc.get("final"):
        elems.append(Boceto(esc["boceto"](), 810, 40, 0.5, rnd))
        elems.append(texto_ajustado("Creado por", 80, 1600, W / 2, 330, color=TINTA))
        elems.append(texto_ajustado("JEISSON SERRANO", 170, 1700, W / 2, 440))
        sub = Boceto([(AZUL, 8, [(0, 0), (300, 12), (600, 0)])], 660, 700, 1.0, rnd)
        sub.peso = 0.8
        elems.append(sub)
        elems.append(texto_ajustado("Máster en Inteligencia Artificial", 80, 1700, W / 2, 760))
        return elems
    elems.append(texto_ajustado(esc["titulo"], 100, 1720, W / 2, 50))
    elems.append(Boceto(esc["boceto"](), 170, 250, 1.2, rnd))
    y = 360
    for p in esc["puntos"]:
        t = Texto(p, 66, 0, y, punto=True, x=1000)
        if t.img.width > 860:
            t = Texto(p, 54, 0, y, punto=True, x=1000)
        elems.append(t)
        y += 140
    return elems


def programar(elems, t_ini, t_fin):
    """Asigna a cada elemento (inicio, duración) dentro de la ventana disponible."""
    hueco = 0.3
    pesos = [max(e.peso, 0.6) for e in elems]
    disponible = (t_fin - t_ini) - hueco * (len(elems) - 1)
    k = min(1.0, disponible / sum(pesos))
    t = t_ini
    plan = []
    for e, p in zip(elems, pesos):
        d = p * k
        plan.append((e, t, d))
        t += d + hueco
    return plan


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------


def narrar():
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin"))
    clips = []
    for esc in ESCENAS:
        s, sr = k.create(esc["voz"], voice=VOZ, speed=0.95, lang="es")
        assert sr == SR
        clips.append(np.asarray(s, dtype=np.float32))
    return clips


def musica(dur):
    """Colchón musical ambiental suave (acordes Am - F - C - G)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    acordes = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63],
               [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    dur_ac = 4.0
    out = np.zeros(n, dtype=np.float64)
    for i in range(int(dur / dur_ac) + 1):
        a0 = int(i * dur_ac * SR)
        a1 = min(n, int((i + 1) * dur_ac * SR + SR))
        if a0 >= n:
            break
        tt = t[a0:a1] - t[a0]
        env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, (dur_ac + 1 - tt)) / 1.5)
        for f in acordes[i % 4]:
            for det in (0.997, 1.003):
                out[a0:a1] += np.sin(2 * np.pi * f * det * tt) * env
            out[a0:a1] += 0.3 * np.sin(2 * np.pi * f / 2 * tt) * env
    out /= np.max(np.abs(out)) + 1e-9
    fade = np.minimum(1, np.minimum(t / 2, (dur - t) / 3))
    return out * fade * 0.07


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def fondo_pizarra():
    img = Image.new("RGB", (W, H), PIZARRA)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = np.clip(1 - 0.06 * r ** 2, 0, 1)
    arr = (np.asarray(img).astype(np.float32) * v[..., None]).astype(np.uint8)
    return Image.fromarray(arr)


def cargar_mano():
    m = Image.open(os.path.join(REC, "mano.png")).convert("RGBA")
    esc = 0.62
    m = m.resize((int(m.width * esc), int(m.height * esc)), Image.LANCZOS)
    punta = (62 * esc, 510 * esc)  # punta del marcador en la imagen
    sombra = Image.new("RGBA", m.size, (0, 0, 0, 0))
    sombra.putalpha(m.getchannel("A").point(lambda a: int(a * 0.25)))
    sombra = sombra.filter(ImageFilter.GaussianBlur(10))
    return m, sombra, punta


def main():
    print("Generando narración...")
    clips = narrar()
    duraciones = [SLIDE + 0.3 + len(c) / SR + PAUSA_FIN for c in clips]
    duraciones[-1] += 1.5
    total = sum(duraciones)

    audio = np.zeros(int(total * SR) + SR, dtype=np.float64)
    t0 = 0.0
    for c, d in zip(clips, duraciones):
        a = int((t0 + SLIDE + 0.3) * SR)
        audio[a:a + len(c)] += c / (np.max(np.abs(c)) + 1e-9) * 0.9
        t0 += d
    audio[:len(audio)] += musica(len(audio) / SR)
    audio = np.clip(audio, -1, 1)
    sf.write(TMP_WAV, audio.astype(np.float32), SR)

    fondo = fondo_pizarra()
    fondo2x = fondo.resize((W * SS, H * SS))
    mano, sombra, punta_off = cargar_mano()

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", TMP_WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
           "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    mano_pos = [W + 300.0, H + 400.0]
    anterior = None  # último cuadro de la escena anterior (para la transición)
    frame_global = 0
    for idx, (esc, dur) in enumerate(zip(ESCENAS, duraciones)):
        print(f"Escena {idx + 1}/{len(ESCENAS)} ({dur:.1f}s)")
        elems = construir(esc, idx)
        plan = programar(elems, SLIDE + 0.2, dur - 0.6)
        lienzo2x = fondo2x.copy()
        capa_txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hechos = set()
        n = int(round(dur * FPS))
        for f in range(n):
            t = f / FPS
            punta = None
            parcial = None
            for j, (e, ti, d) in enumerate(plan):
                if t < ti or j in hechos:
                    continue
                p = min(1.0, (t - ti) / d)
                if isinstance(e, Boceto):
                    pt = e.avanzar(p, lienzo2x)
                    if p < 1:
                        punta = pt
                else:
                    if p < 1:
                        parcial = (e, p)
                        punta = e.punta(p, t)
                    else:
                        capa_txt.alpha_composite(e.img, (e.x, e.y))
                if p >= 1:
                    hechos.add(j)
            cuadro = lienzo2x.reduce(SS).convert("RGBA")
            cuadro.alpha_composite(capa_txt)
            if parcial:
                e, p = parcial
                cuadro.alpha_composite(e.parcial(p), (e.x, e.y))

            # mano: sigue la punta al dibujar; si no, se retira fuera de cuadro
            if punta is not None and t >= SLIDE:
                dist = math.hypot(punta[0] - mano_pos[0], punta[1] - mano_pos[1])
                if dist > 40:  # llega desde fuera de cuadro
                    mano_pos[0] += (punta[0] - mano_pos[0]) * 0.45
                    mano_pos[1] += (punta[1] - mano_pos[1]) * 0.45
                else:
                    mano_pos = [punta[0], punta[1]]
            else:
                objetivo = (W + 250, H + 450)
                mano_pos[0] += (objetivo[0] - mano_pos[0]) * 0.18
                mano_pos[1] += (objetivo[1] - mano_pos[1]) * 0.18
            hx, hy = int(mano_pos[0] - punta_off[0]), int(mano_pos[1] - punta_off[1])
            if hx < W and hy < H:
                cuadro.paste((0, 0, 0, 255), (hx + 18, hy + 22), sombra)
                cuadro.paste(mano, (hx, hy), mano)
            cuadro = cuadro.convert("RGB")

            # transición: la pizarra anterior se desliza hacia la izquierda
            if anterior is not None and t < SLIDE:
                u = t / SLIDE
                u = u * u * (3 - 2 * u)
                off = int(W * u)
                comp = Image.new("RGB", (W, H))
                comp.paste(anterior, (-off, 0))
                comp.paste(cuadro, (W - off, 0))
                cuadro = comp
            if frame_global < int(0.5 * FPS):
                cuadro = Image.blend(Image.new("RGB", (W, H), PIZARRA), cuadro, frame_global / (0.5 * FPS))
            proc.stdin.write(cuadro.tobytes())
            frame_global += 1
        anterior = cuadro
    proc.stdin.close()
    proc.wait()
    os.remove(TMP_WAV)
    print("Listo:", OUT)


if __name__ == "__main__":
    main()
