"""Película cinematográfica: APOCALIPSIS — los cuatro jinetes y las dos bestias.

Cada escena usa una imagen preparada (preparar_imagenes.py: ampliada, rostros
restaurados y mapa de profundidad) animada con cámara 2.5D (paralaje real por
profundidad), niebla volumétrica, fuego, brasas, lluvia, relámpagos, meteoros,
rayos de luz, bloom, gradación de color, grano y formato 2.39:1. Narración en
español con subtítulos, banda sonora orquestal y efectos de sonido generados
por código. Termina con una leyenda del Apocalipsis (22:12-13).

Uso:  python3 generar_pelicula.py            ->  apocalipsis.mp4
      PRUEBA=3,9 python3 generar_pelicula.py ->  prueba de escenas sueltas
Requiere: numpy opencv-python-headless pillow soundfile kokoro-onnx imageio-ffmpeg
Voz: KOKORO_DIR con kokoro-v1.0.onnx y voices-v1.0.bin.
"""
import math
import os
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(AQUI, "recursos")
LISTAS = os.path.join(REC, "listas")
KOKORO_DIR = os.environ.get("KOKORO_DIR", REC)
PRUEBA = os.environ.get("PRUEBA")
OUT = os.path.join(AQUI, "apocalipsis.mp4" if not PRUEBA else "prueba.mp4")
TMP_WAV = os.path.join(AQUI, "_audio.wav")

W, H, FPS = 1920, 1080, 30
SR = 44100
BARRA = 138
FUNDIDO = 1.0
F_TITULO = os.path.join(REC, "Cinzel.ttf")
F_SUB = os.path.join(REC, "Lora.ttf")
F_GRIEGO = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
ORO = (226, 186, 104)

# cam: z=(zoom ini, fin), c=(centro ini, fin), dolly=zoom extra del primer plano,
#      pan=desplazamiento de paralaje del primer plano (px), temblor=px
ESCENAS = [
    dict(img="01_patmos", tono="vela", musica="misterio",
         cam=dict(z=(1.0, 1.13), c=((0.5, 0.5), (0.46, 0.45)), dolly=0.07, pan=(-40, 0)),
         fx=["polvo"], cap=("PATMOS", "Apocalipsis 1:9-11"),
         voz=["En la isla de Patmos, desterrado por su fe, el apóstol Juan recibió una visión.",
              "La revelación de las cosas que habían de suceder al final de los tiempos."]),
    dict(img="02_sellos", tono="dorado", musica="misterio", sfx=["campana"],
         cam=dict(z=(1.05, 1.22), c=((0.5, 0.52), (0.5, 0.5)), dolly=0.09, pan=(0, -20)),
         fx=["polvo", "luz"], luz=(0.5, 0.05), cap=("EL LIBRO DE LOS SIETE SELLOS", "Apocalipsis 5:1-5"),
         voz=["Vi en la mano del que estaba sentado en el trono un libro sellado con siete sellos.",
              "Y nadie era digno de abrirlo... sino el Cordero."]),
    dict(img="03_caballo_blanco", tono="epico", musica="jinetes", sfx=["campana", "galope"],
         cam=dict(z=(1.18, 1.02), c=((0.52, 0.45), (0.5, 0.5)), dolly=0.1, pan=(-70, 0), temblor=2),
         fx=["polvo", "niebla"], cap=("EL PRIMER SELLO", "Apocalipsis 6:2"),
         voz=["Cuando el Cordero abrió el primer sello, miré, y he aquí un caballo blanco.",
              "El que lo montaba tenía un arco, y le fue dada una corona.",
              "Y salió venciendo, y para vencer."]),
    dict(img="04_caballo_rojo", tono="sangre", musica="jinetes", sfx=["campana", "galope", "fuego"],
         cam=dict(z=(1.0, 1.16), c=((0.5, 0.5), (0.52, 0.42)), dolly=0.11, pan=(60, 0), temblor=2),
         fx=["brasas", "humo", "fuego"], cap=("EL SEGUNDO SELLO", "Apocalipsis 6:3-4"),
         voz=["Y salió otro caballo, bermejo.",
              "Al que lo montaba le fue dado poder de quitar la paz de la tierra, y que se mataran unos a otros.",
              "Y le fue dada una gran espada."]),
    dict(img="05_caballo_negro", tono="hambre", musica="jinetes", sfx=["campana", "viento"],
         cam=dict(z=(1.12, 1.0), c=((0.45, 0.45), (0.5, 0.5)), dolly=0.08, pan=(-50, 0)),
         fx=["ceniza", "niebla"], cap=("EL TERCER SELLO", "Apocalipsis 6:5-6"),
         voz=["Y miré, y he aquí un caballo negro. El que lo montaba tenía una balanza en su mano.",
              "Y oí una voz que decía: dos libras de trigo por un denario... y no hagas daño al vino ni al aceite."]),
    dict(img="06_caballo_amarillo", tono="muerte", musica="terror", sfx=["campana", "latido"],
         cam=dict(z=(1.0, 1.18), c=((0.5, 0.5), (0.5, 0.44)), dolly=0.12, pan=(0, -30)),
         fx=["niebla_densa", "ceniza"], cap=("EL CUARTO SELLO", "Apocalipsis 6:7-8"),
         voz=["Y miré, y he aquí un caballo amarillo.",
              "El que lo montaba tenía por nombre Muerte, y el Hades le seguía.",
              "Y le fue dada potestad sobre la cuarta parte de la tierra."]),
    dict(img="07_cuatro_jinetes", tono="infierno", musica="jinetes", sfx=["galope"],
         cam=dict(z=(1.2, 1.0), c=((0.5, 0.52), (0.5, 0.5)), dolly=0.14, pan=(0, 0), temblor=4),
         fx=["brasas", "humo"], cap=("LOS CUATRO JINETES", "Apocalipsis 6:1-8"),
         voz=["Cuatro jinetes. Conquista. Guerra. Hambre. Y Muerte.",
              "Cabalgando juntos sobre la tierra."]),
    dict(img="08_sexto_sello", tono="sangre_oscuro", musica="terror", sfx=["campana", "terremoto"],
         cam=dict(z=(1.05, 1.2), c=((0.5, 0.5), (0.5, 0.45)), dolly=0.08, pan=(0, 20), temblor=9),
         fx=["meteoros", "ceniza"], cap=("EL SEXTO SELLO", "Apocalipsis 6:12-13"),
         voz=["Y hubo un gran terremoto. El sol se puso negro como un saco de cilicio, y la luna se volvió toda como sangre.",
              "Y las estrellas del cielo cayeron sobre la tierra."]),
    dict(img="09_bestia_mar", tono="tormenta", musica="terror", sfx=["olas", "rugido", "trueno"],
         cam=dict(z=(1.0, 1.15), c=((0.5, 0.55), (0.5, 0.45)), dolly=0.12, pan=(0, -40), temblor=3),
         fx=["lluvia", "rayos", "niebla"], cap=("LA BESTIA DEL MAR", "Apocalipsis 13:1"),
         voz=["Y vi una bestia subir del mar, que tenía siete cabezas y diez cuernos.",
              "Y sobre sus cuernos, diez diademas. Y sobre sus cabezas, un nombre de blasfemia."]),
    dict(img="10_bestia_cabeza", tono="tormenta", musica="terror", sfx=["rugido", "trueno"],
         cam=dict(z=(1.0, 1.22), c=((0.5, 0.5), (0.5, 0.45)), dolly=0.15, pan=(30, 0), temblor=3),
         fx=["lluvia", "rayos"], cap=("", "Apocalipsis 13:2"),
         voz=["La bestia era semejante a un leopardo. Sus pies, como de oso. Y su boca, como boca de león.",
              "Y el dragón le dio su poder, su trono, y grande autoridad."]),
    dict(img="11_bestia_tierra", tono="infierno", musica="terror", sfx=["terremoto", "fuego", "rugido"],
         cam=dict(z=(1.15, 1.0), c=((0.5, 0.45), (0.5, 0.5)), dolly=0.12, pan=(-50, 0), temblor=3),
         fx=["brasas", "humo", "fuego"], cap=("LA BESTIA DE LA TIERRA", "Apocalipsis 13:11-13"),
         voz=["Después vi otra bestia que subía de la tierra.",
              "Tenía dos cuernos semejantes a los de un cordero, pero hablaba como dragón.",
              "Y hacía descender fuego del cielo delante de los hombres."]),
    dict(img="12_marca", tono="infierno_oscuro", musica="terror", sfx=["latido"],
         cam=dict(z=(1.0, 1.25), c=((0.5, 0.5), (0.5, 0.5)), dolly=0.1, pan=(0, 0)),
         fx=["brasas", "humo", "pulso"], cap=("EL NÚMERO DE LA BESTIA", "Apocalipsis 13:16-18"),
         voz=["Y hacía que a todos se les pusiera una marca en la mano derecha, o en la frente.",
              "Aquí hay sabiduría. El que tiene entendimiento, cuente el número de la bestia, pues es número de hombre.",
              "Y su número es seiscientos sesenta y seis."]),
    dict(img="13_fiel_verdadero", tono="gloria", musica="gloria", sfx=["trompeta"],
         cam=dict(z=(1.2, 1.0), c=((0.5, 0.45), (0.5, 0.5)), dolly=0.12, pan=(0, 30)),
         fx=["luz", "polvo"], luz=(0.5, 0.15), cap=("FIEL Y VERDADERO", "Apocalipsis 19:11-12"),
         voz=["Entonces vi el cielo abierto, y he aquí un caballo blanco.",
              "El que lo montaba se llamaba Fiel y Verdadero. Sus ojos eran como llama de fuego, y en su cabeza había muchas diademas."]),
    dict(img="14_nueva_jerusalen", tono="gloria", musica="gloria",
         cam=dict(z=(1.0, 1.18), c=((0.5, 0.55), (0.5, 0.45)), dolly=0.1, pan=(0, -30)),
         fx=["luz", "polvo", "niebla"], luz=(0.5, 0.3), cap=("LA NUEVA JERUSALÉN", "Apocalipsis 21:1-4"),
         voz=["Y vi un cielo nuevo y una tierra nueva. Y la santa ciudad, la nueva Jerusalén, descendía del cielo.",
              "Y Dios enjugará toda lágrima de sus ojos. Y ya no habrá muerte, ni llanto, ni clamor, ni dolor."]),
]

LEYENDA = [
    "«He aquí, yo vengo pronto, y mi galardón conmigo,",
    "para recompensar a cada uno según sea su obra.",
    "Yo soy el Alfa y la Omega, el principio y el fin,",
    "el primero y el último.»",
]
LEYENDA_REF = "APOCALIPSIS 22:12-13"
LEYENDA_VOZ = ["He aquí, yo vengo pronto, y mi galardón conmigo, para recompensar a cada uno según sea su obra.",
               "Yo soy el Alfa y la Omega, el principio y el fin, el primero y el último."]
TITULO_VOZ = None

# (mult sombras, mult luces, saturación, contraste, brillo)
TONOS = {
    "vela": ((0.85, 0.9, 1.05), (1.12, 1.0, 0.8), 1.0, 1.15, 0.95),
    "dorado": ((0.9, 0.9, 1.0), (1.15, 1.03, 0.78), 1.05, 1.15, 1.0),
    "epico": ((0.82, 0.95, 1.12), (1.1, 1.0, 0.85), 0.95, 1.2, 1.0),
    "sangre": ((0.95, 0.85, 0.85), (1.15, 0.92, 0.8), 1.05, 1.22, 0.95),
    "sangre_oscuro": ((0.9, 0.8, 0.85), (1.15, 0.9, 0.8), 1.0, 1.28, 0.88),
    "hambre": ((0.9, 0.95, 1.0), (1.02, 1.0, 0.95), 0.55, 1.2, 0.92),
    "muerte": ((0.85, 1.0, 0.95), (0.98, 1.04, 0.92), 0.5, 1.2, 0.88),
    "infierno": ((0.9, 0.85, 0.9), (1.18, 0.98, 0.75), 1.1, 1.22, 0.95),
    "infierno_oscuro": ((0.85, 0.8, 0.85), (1.2, 0.95, 0.72), 1.1, 1.3, 0.85),
    "tormenta": ((0.82, 0.92, 1.12), (0.95, 1.0, 1.06), 0.7, 1.25, 0.9),
    "gloria": ((0.95, 0.95, 1.0), (1.12, 1.05, 0.88), 1.05, 1.08, 1.06),
}
NIEBLA_COLOR = {"vela": (60, 45, 30), "dorado": (120, 100, 70), "epico": (110, 115, 120),
                "sangre": (90, 40, 30), "sangre_oscuro": (60, 20, 20), "hambre": (95, 95, 90),
                "muerte": (95, 110, 100), "infierno": (110, 55, 30), "infierno_oscuro": (70, 30, 20),
                "tormenta": (70, 80, 95), "gloria": (220, 200, 160)}

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


def graduar(img, tono):
    s_mul, l_mul, sat, con, bri = TONOS[tono]
    a = img.astype(np.float32) / 255.0
    lum = (a * [0.299, 0.587, 0.114]).sum(axis=2, keepdims=True)
    a = lum + (a - lum) * sat
    a = (a - 0.5) * con + 0.5
    a *= bri
    wl = np.clip(lum, 0, 1)
    a *= np.array(s_mul, np.float32) * (1 - wl) + np.array(l_mul, np.float32) * wl
    a = np.clip(a, 0, 1)
    a = a * a * (3 - 2 * a) * 0.3 + a * 0.7
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def ruido_tileable(w, h, semilla, escala=40.0):
    rnd = np.random.default_rng(semilla)
    f = np.fft.fft2(rnd.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * h
    fx = np.fft.fftfreq(w)[None, :] * w
    r = np.sqrt(fx ** 2 + fy ** 2) + 1e-6
    f *= np.exp(-(r / escala) ** 2) / r ** 0.9
    n = np.real(np.fft.ifft2(f))
    n = (n - n.min()) / (n.max() - n.min())
    return n.astype(np.float32)


class Escena:
    def __init__(self, esc, idx):
        self.e = esc
        self.idx = idx
        img = np.asarray(Image.open(os.path.join(LISTAS, esc["img"] + ".jpg")).convert("RGB"))
        prof = np.asarray(Image.open(os.path.join(LISTAS, esc["img"] + "_prof.png")), dtype=np.float32) / 65535.0
        ancho = 2400
        alto = int(img.shape[0] * ancho / img.shape[1])
        img = cv2.resize(img, (ancho, alto), interpolation=cv2.INTER_AREA)
        self.src = graduar(img, esc["tono"])
        self.prof = cv2.resize(prof, (ancho // 2, alto // 2), interpolation=cv2.INTER_AREA)
        self.Ws, self.Hs = ancho, alto
        rnd = np.random.default_rng(idx)
        self.rnd = rnd
        n = 160
        self.pp = rnd.random((n, 5)).astype(np.float32)  # partículas

    def mapas(self, u, t):
        """Mapas de muestreo (media resolución) con paralaje por profundidad."""
        cam = self.e["cam"]
        e = u * u * (3 - 2 * u) * 0.35 + u * 0.65
        z = cam["z"][0] + (cam["z"][1] - cam["z"][0]) * e
        cx = cam["c"][0][0] + (cam["c"][1][0] - cam["c"][0][0]) * e
        cy = cam["c"][0][1] + (cam["c"][1][1] - cam["c"][0][1]) * e
        tem = cam.get("temblor", 0)
        if tem:
            cx += tem / W * (math.sin(t * 13.1) + 0.6 * math.sin(t * 29.7 + 1)) * 0.5
            cy += tem / H * (math.sin(t * 11.3 + 2) + 0.6 * math.sin(t * 23.9)) * 0.5
        cw = self.Ws / z
        ch = cw * H / W
        if ch > self.Hs / z * 1.0001:
            ch = self.Hs / z
            cw = ch * W / H
        Cx = min(max(cw / 2, cx * self.Ws), self.Ws - cw / 2)
        Cy = min(max(ch / 2, cy * self.Hs), self.Hs - ch / 2)
        h2, w2 = H // 2, W // 2
        gx = (np.arange(w2, dtype=np.float32) + 0.5) / w2 - 0.5
        gy = (np.arange(h2, dtype=np.float32) + 0.5) / h2 - 0.5
        GX, GY = np.meshgrid(gx, gy)
        bx = Cx + GX * cw
        by = Cy + GY * ch
        d = cv2.remap(self.prof, bx / 2, by / 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        dd = d - 0.45
        k = 1.0 + cam.get("dolly", 0) * e * dd
        px, py = cam.get("pan", (0, 0))
        mx = Cx + GX * cw / k - px * (e - 0.5) * dd * (cw / W) * 2
        my = Cy + GY * ch / k - py * (e - 0.5) * dd * (ch / H) * 2
        return mx, my, d

    def cuadro(self, t, dur, niebla):
        u = min(1.0, max(0.0, t / dur))
        mx, my, d = self.mapas(u, t)
        MX = cv2.resize(mx, (W, H), interpolation=cv2.INTER_LINEAR)
        MY = cv2.resize(my, (W, H), interpolation=cv2.INTER_LINEAR)
        fr = cv2.remap(self.src, MX, MY, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        fx = self.e["fx"]
        D = cv2.resize(d, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]

        if "fuego" in fx:
            fl = 1 + 0.05 * math.sin(t * 17) + 0.035 * math.sin(t * 29 + 1) + 0.02 * math.sin(t * 43 + 2)
            fr *= fl
        if "pulso" in fx:
            p = 0.5 + 0.5 * math.sin(t * 2 * math.pi / 1.6)
            fr[..., 0] *= 1 + 0.08 * p
        # niebla volumétrica: más densa a lo lejos
        if any(f.startswith("niebla") or f == "humo" for f in fx):
            dens = 0.55 if "niebla_densa" in fx else 0.32
            if "humo" in fx:
                dens = max(dens, 0.28)
            n1 = cv2.warpAffine(niebla[0], np.float32([[1, 0, -t * 18], [0, 1, -t * 3]]), (W // 2, H // 2),
                                borderMode=cv2.BORDER_WRAP)
            n2 = cv2.warpAffine(niebla[1], np.float32([[1, 0, t * 9], [0, 1, -t * 6 if "humo" in fx else t * 2]]),
                                (W // 2, H // 2), borderMode=cv2.BORDER_WRAP)
            nf = cv2.resize(n1 * 0.6 + n2 * 0.4, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
            a = np.clip((nf - 0.25) * 1.6, 0, 1) * dens * (1 - D * 0.85)
            col = np.array(NIEBLA_COLOR[self.e["tono"]], np.float32)
            fr = fr * (1 - a) + col * a

        # relámpagos
        if "rayos" in fx:
            for tr in (1.3, 5.2, 8.8):
                dt = t - tr
                if 0 <= dt < 0.5:
                    k = (1 - dt / 0.5) * (1.0 if dt < 0.06 or 0.12 < dt < 0.19 else 0.35)
                    fr += np.array([150, 160, 190], np.float32) * k * (1.1 - D * 0.7)

        # partículas
        cap = np.zeros((H, W, 3), np.float32)
        P = self.pp
        if "brasas" in fx:
            for x, y, v, f, r in P[:120].tolist():
                xx = (x * W + 40 * math.sin(t * 1.5 + f * 9)) % W
                yy = (y * H - t * (60 + 120 * v)) % H
                a = 0.6 + 0.4 * math.sin(t * 6 + f * 20)
                cv2.circle(cap, (int(xx), int(yy)), int(1 + r * 2.5), (255 * a, (120 + 90 * v) * a, 30 * a), -1,
                           cv2.LINE_AA)
        if "polvo" in fx:
            for x, y, v, f, r in P[:90].tolist():
                xx = (x * W + t * 12 * v + 30 * math.sin(t * 0.4 + f * 7)) % W
                yy = (y * H - t * 5 * v + 20 * math.cos(t * 0.3 + f * 5)) % H
                a = 0.35 + 0.3 * math.sin(t * 0.8 + f * 11)
                cv2.circle(cap, (int(xx), int(yy)), int(1 + r * 2), (200 * a, 185 * a, 160 * a), -1, cv2.LINE_AA)
        if "ceniza" in fx:
            for x, y, v, f, r in P[:140].tolist():
                xx = (x * W + t * 25 + 40 * math.sin(t * 0.7 + f * 6)) % W
                yy = (y * H + t * (30 + 40 * v)) % H
                c = 60 + 50 * v
                cv2.circle(cap, (int(xx), int(yy)), int(1 + r * 2), (c, c, c), -1, cv2.LINE_AA)
        if "lluvia" in fx:
            for x, y, v, f, r in P.tolist():
                xx = (x * W + t * 300) % W
                yy = (y * H + t * (1400 + 600 * v)) % H
                cv2.line(cap, (int(xx), int(yy)), (int(xx - 10), int(yy - 45 - 30 * v)), (70, 75, 85), 1,
                         cv2.LINE_AA)
        if "meteoros" in fx:
            for x, y, v, f, r in P[:14].tolist():
                per = 2.5 + 3 * v
                fase = ((t + f * per) % per) / per
                if fase < 0.4:
                    q = fase / 0.4
                    x0, y0 = x * W, -50 + y * H * 0.2
                    xx, yy = x0 - q * 700, y0 + q * 600
                    cv2.line(cap, (int(xx), int(yy)), (int(xx + 160), int(yy - 140)), (255, 170, 90), 3,
                             cv2.LINE_AA)
                    cv2.circle(cap, (int(xx), int(yy)), 6, (255, 230, 190), -1, cv2.LINE_AA)
        fr += cap

        # rayos de luz (desenfoque radial de las zonas brillantes)
        if "luz" in fx:
            lx, ly = self.e.get("luz", (0.5, 0.2))
            q = cv2.resize(np.clip(fr, 0, 255), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            q = np.clip(q - 150, 0, 255) * 1.6
            acc = np.zeros_like(q)
            c = (lx * W / 4, ly * H / 4)
            for i in range(1, 11):
                s = 1 + i * 0.045
                M = np.float32([[s, 0, c[0] * (1 - s)], [0, s, c[1] * (1 - s)]])
                acc += cv2.warpAffine(q, M, (W // 4, H // 4)) * (1 - i / 12)
            acc = cv2.GaussianBlur(acc, (0, 0), 3) / 6 * (0.85 + 0.15 * math.sin(t * 0.9))
            fr += cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)

        # bloom
        q = cv2.resize(np.clip(fr, 0, 255), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        q = np.clip(q - 185, 0, 255)
        q = cv2.GaussianBlur(q, (0, 0), 9)
        fr += cv2.resize(q, (W, H), interpolation=cv2.INTER_LINEAR) * 0.55
        return fr


# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------


def texto_img(lineas, f, color, sombra=6, espacio=1.3, tracking=0):
    if isinstance(lineas, str):
        lineas = [lineas]

    def ancho(l):
        return f.getlength(l) + tracking * max(0, len(l) - 1)

    alto = int(f.size * espacio)
    w = int(max(ancho(l) for l in lineas)) + 60
    h = alto * len(lineas) + 60
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    som = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for capa, col in ((som, (0, 0, 0, 230)), (img, color)):
        d = ImageDraw.Draw(capa)
        for k, l in enumerate(lineas):
            x = (w - ancho(l)) / 2
            y = 30 + k * alto
            if tracking:
                for ch in l:
                    d.text((x, y), ch, font=f, fill=col)
                    x += f.getlength(ch) + tracking
            else:
                d.text((x, y), l, font=f, fill=col)
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base.alpha_composite(som.filter(ImageFilter.GaussianBlur(sombra)))
    base.alpha_composite(img)
    return np.asarray(base).astype(np.float32)


def envolver(texto, f, ancho):
    out, act = [], ""
    for p in texto.split():
        pr = (act + " " + p).strip()
        if f.getlength(pr) <= ancho:
            act = pr
        else:
            out.append(act)
            act = p
    out.append(act)
    return out


def pegar(fr, rgba, x, y, alfa):
    if alfa <= 0.001:
        return
    h, w = rgba.shape[:2]
    x, y = int(x), int(y)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    sub = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = sub[..., 3:4] / 255.0 * alfa
    fr[y0:y1, x0:x1] = fr[y0:y1, x0:x1] * (1 - a) + sub[..., :3] * a


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------


def remuestrear(x, sr_in, sr_out):
    n = int(len(x) * sr_out / sr_in)
    return np.interp(np.arange(n) * sr_in / sr_out, np.arange(len(x)), x).astype(np.float32)


def narrar(textos):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin"))
    out = []
    for txt in textos:
        s, sr = k.create(txt, voice="em_alex", speed=0.93, lang="es")
        s = np.asarray(s, np.float64)
        # voz más grave (-1 semitono, algo más pausada)
        s = remuestrear(s, sr * 1.06, SR)
        s = s / (np.max(np.abs(s)) + 1e-9)
        s = np.tanh(s * 1.6) / np.tanh(1.6)  # compresión suave
        out.append(s.astype(np.float32) * 0.9)
    return out


def pasa_bajos(x, k):
    if k <= 1:
        return x
    c = np.cumsum(np.insert(x, 0, 0.0))
    y = (c[k:] - c[:-k]) / k
    return np.concatenate([np.full(k - 1, y[0]), y])


def reverb(x, seg=3.0, mezcla=0.35, semilla=9):
    n = int(seg * SR)
    rnd = np.random.default_rng(semilla)
    ir = rnd.standard_normal(n) * np.exp(-np.arange(n) / (SR * seg / 6.5))
    ir[:int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    N = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:len(x)]
    y *= (np.std(x) + 1e-9) / (np.std(y) + 1e-9)
    return x * (1 - mezcla) + y * mezcla


def aditivo(f, dur, amps, vibr=0.0, fase=0.0):
    t = np.arange(int(dur * SR)) / SR
    ph = 2 * np.pi * f * t + (vibr * np.sin(2 * np.pi * 5.2 * t) / 5.2 * f * 0.006 * 2 * np.pi if vibr else 0)
    out = np.zeros_like(t)
    for h, a in enumerate(amps, 1):
        if f * h > SR / 2 - 500:
            break
        out += a * np.sin(ph * h + fase * h)
    return out


def env_adsr(n, a, r, s=1.0):
    e = np.ones(n) * s
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    e[:na] = np.linspace(0, s, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def nota_cuerdas(f, dur):
    amps = [1 / h * 0.9 ** h for h in range(1, 16)]
    x = sum(aditivo(f * d, dur, amps, vibr=1.0, fase=i) for i, d in enumerate((0.997, 1.0, 1.003)))
    return pasa_bajos(x, 6) * env_adsr(len(x), min(1.5, dur / 3), min(1.8, dur / 3))


def nota_coro(f, dur):
    forman = [(800, 90), (1150, 110), (2900, 150)]
    amps = []
    for h in range(1, 30):
        fh = f * h
        amps.append(sum(math.exp(-((fh - fc) / bw) ** 2 / 2) * g for (fc, bw), g in zip(forman, (1, 0.6, 0.25)))
                    + 0.3 / h)
    x = sum(aditivo(f * d, dur, amps, vibr=1.5, fase=i * 0.7) for i, d in enumerate((0.995, 1.0, 1.005, 1.01)))
    return x * env_adsr(len(x), min(2.0, dur / 3), min(2.0, dur / 3))


def nota_metal(f, dur):
    t = np.arange(int(dur * SR)) / SR
    brillo = 2 + 10 * np.clip(t / 0.35, 0, 1) * np.exp(-t / (dur * 0.9))
    out = np.zeros_like(t)
    for h in range(1, 22):
        out += np.sin(2 * np.pi * f * h * t) * np.exp(-h / brillo) / h ** 0.6
    return out * env_adsr(len(t), 0.08, min(0.8, dur / 2))


def taiko(fuerza=1.0):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 48 + 60 * np.exp(-t * 18)
    cuerpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    rnd = np.random.default_rng(int(fuerza * 1000) % 97)
    golpe = pasa_bajos(rnd.standard_normal(n), 8) * np.exp(-t * 40) * 0.6
    return (cuerpo + golpe) * fuerza


def campana(f0=98.0, dur=7.0):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for r, a, dec in [(0.5, 0.6, 0.35), (1.0, 1.0, 0.5), (1.19, 0.7, 0.7), (1.56, 0.5, 0.9), (2.0, 0.45, 1.1),
                      (2.51, 0.35, 1.4), (2.66, 0.3, 1.5), (3.01, 0.25, 1.8), (4.1, 0.15, 2.5)]:
        out += a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * dec)
    return out * np.minimum(1, t / 0.004)


def ruido_filtrado(n, k, semilla):
    rnd = np.random.default_rng(semilla)
    x = pasa_bajos(rnd.standard_normal(n), k)
    return x / (np.max(np.abs(x)) + 1e-9)


def galope(dur, semilla):
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.0
    rnd = np.random.default_rng(semilla)
    golpe_n = int(0.09 * SR)
    tt = np.arange(golpe_n) / SR
    while t < dur - 0.2:
        for off in (0.0, 0.085, 0.17):
            a = int((t + off) * SR)
            if a + golpe_n >= n:
                break
            g = pasa_bajos(rnd.standard_normal(golpe_n), 25) * np.exp(-tt * 45)
            g += np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 30) * 0.8
            out[a:a + golpe_n] += g * rnd.uniform(0.7, 1.0)
        t += 0.42
    return out / (np.max(np.abs(out)) + 1e-9)


def rugido(dur, semilla):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / 0.25) * np.exp(-np.maximum(0, t - dur * 0.55) * 3)
    f = 55 + 20 * np.sin(2 * np.pi * 3 * t) + 8 * np.random.default_rng(semilla).standard_normal(n).cumsum() / SR
    base = np.zeros(n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    for h in range(1, 18):
        base += np.sin(ph * h) / h
    ruido = ruido_filtrado(n, 5, semilla) * 0.8
    x = pasa_bajos(base * 0.7 + ruido * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t)), 3)
    return x / (np.max(np.abs(x)) + 1e-9) * env


def trueno(semilla):
    n = int(4.5 * SR)
    t = np.arange(n) / SR
    x = ruido_filtrado(n, 60, semilla) * 0.8 + ruido_filtrado(n, 12, semilla + 1) * 0.3
    env = np.minimum(1, t / 0.02) * np.exp(-t * 1.1) * (1 + 0.5 * np.sin(t * 19))
    return x * env


def banda_sonora(total, plan, titulo_fin, leyenda_ini):
    n = int(total * SR)
    mus = np.zeros(n)
    sfx = np.zeros(n)
    t_all = np.arange(n) / SR

    def poner(dst, x, t0, g=1.0):
        a = int(t0 * SR)
        if a >= n:
            return
        L = min(len(x), n - a)
        dst[a:a + L] += x[:L] * g

    # drone grave continuo (Re)
    drone = np.zeros(n)
    for h, a in [(1, 1.0), (2, 0.45), (3, 0.2), (5, 0.08)]:
        drone += a * np.sin(2 * np.pi * 36.71 * h * t_all + h)
    mus += drone * 0.16 * (0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * t_all))

    menor = [[73.42, 87.31, 110.0], [58.27, 87.31, 116.54], [65.41, 98.0, 130.81], [55.0, 82.41, 110.0]]
    terror = [[73.42, 77.78, 110.0], [69.3, 73.42, 103.83], [73.42, 87.31, 103.83]]
    mayor = [[73.42, 92.5, 110.0], [98.0, 123.47, 146.83], [110.0, 138.59, 164.81], [73.42, 92.5, 110.0]]

    # intro: coro misterioso
    for f in (146.83, 174.61, 220.0):
        poner(mus, nota_coro(f, titulo_fin + 1.5), 0.0, 0.035)
    for esc, t0, dur, _ in plan:
        tipo = esc["musica"]
        paso = 4.0 if tipo != "jinetes" else 3.0
        k = 0
        tt = t0
        while tt < t0 + dur - 0.5:
            dd = min(paso + 1.5, t0 + dur + 1.0 - tt)
            prog = {"misterio": menor, "jinetes": menor, "terror": terror, "gloria": mayor}[tipo]
            acorde = prog[k % len(prog)]
            for f in acorde:
                poner(mus, nota_cuerdas(f * 2, dd), tt, 0.05)
                if tipo in ("misterio", "gloria", "terror"):
                    poner(mus, nota_coro(f * 4, dd), tt, 0.018 if tipo != "gloria" else 0.03)
            if tipo == "jinetes":
                poner(mus, nota_metal(acorde[0], 1.4), tt, 0.16)
                poner(mus, nota_metal(acorde[0] * 1.5, 1.4), tt, 0.1)
            if tipo == "gloria":
                poner(mus, nota_metal(acorde[0] * 2, dd * 0.8), tt, 0.07)
            k += 1
            tt += paso
        # percusión
        if tipo == "jinetes":
            beat = 0.75
            b = 0
            while t0 + b * beat < t0 + dur:
                patron = [1.0, 0, 0.5, 0.7][b % 4]
                if patron:
                    poner(mus, taiko(patron), t0 + b * beat, 0.5)
                if b % 4 == 2:
                    poner(mus, taiko(0.4), t0 + b * beat + beat / 2, 0.5)
                b += 1
        elif tipo == "terror":
            poner(mus, taiko(1.0), t0 + 0.1, 0.6)
            poner(mus, ruido_filtrado(int(dur * SR), 200, 7) * env_adsr(int(dur * SR), 1.0, 1.5), t0, 0.12)
        # efectos
        for s in esc.get("sfx", []):
            if s == "campana":
                poner(sfx, campana(73.42), t0 + 0.3, 0.35)
            elif s == "galope":
                poner(sfx, galope(dur, int(t0)), t0 + 0.2, 0.22)
            elif s == "fuego":
                cr = ruido_filtrado(int(dur * SR), 3, 11) * 0.3 + ruido_filtrado(int(dur * SR), 30, 12)
                poner(sfx, cr * env_adsr(int(dur * SR), 0.8, 1.0), t0, 0.08)
            elif s == "viento":
                v = ruido_filtrado(int(dur * SR), 90, 13)
                poner(sfx, v * (0.6 + 0.4 * np.sin(np.arange(len(v)) / SR * 0.8)) * env_adsr(len(v), 1, 1.5), t0, 0.3)
            elif s == "latido":
                for i in range(int(dur / 1.1)):
                    lt = taiko(0.6)[:int(0.35 * SR)]
                    poner(sfx, lt, t0 + 0.5 + i * 1.1, 0.35)
                    poner(sfx, lt, t0 + 0.5 + i * 1.1 + 0.28, 0.25)
            elif s == "terremoto":
                r = ruido_filtrado(int(dur * SR), 150, 14) + ruido_filtrado(int(dur * SR), 40, 15) * 0.3
                poner(sfx, r * env_adsr(len(r), 0.6, 2.0), t0, 0.55)
            elif s == "olas":
                L = int(dur * SR)
                o = ruido_filtrado(L, 20, 16) * (0.5 + 0.5 * np.sin(np.arange(L) / SR * 2 * np.pi / 4.5)) ** 2
                poner(sfx, o * env_adsr(L, 1, 1.5), t0, 0.3)
            elif s == "rugido":
                poner(sfx, rugido(3.2, int(t0)), t0 + 1.6, 0.5)
            elif s == "trueno":
                for tr in (1.3, 5.2, 8.8):
                    if tr < dur:
                        poner(sfx, trueno(int(t0 + tr)), t0 + tr + 0.15, 0.7)
            elif s == "trompeta":
                for i, f in enumerate((146.83, 220.0, 293.66)):
                    poner(sfx, nota_metal(f, 2.2), t0 + 0.4 + i * 0.5, 0.18)
        if "rayos" in esc["fx"] and "trueno" not in esc.get("sfx", []):
            for tr in (1.3, 5.2, 8.8):
                if tr < dur:
                    poner(sfx, trueno(int(t0 + tr)), t0 + tr + 0.15, 0.6)
    # golpes de transición
    for esc, t0, dur, _ in plan:
        poner(mus, taiko(1.0), t0, 0.35)
    # leyenda final: acorde sostenido
    for f in (73.42, 110.0, 146.83, 185.0, 220.0):
        poner(mus, nota_cuerdas(f, total - leyenda_ini), leyenda_ini, 0.05)
        poner(mus, nota_coro(f * 2, total - leyenda_ini), leyenda_ini, 0.02)
    poner(sfx, campana(55.0, 9.0), leyenda_ini + 0.5, 0.4)
    poner(sfx, trueno(99), 0.6, 0.5)
    mus = reverb(mus, 3.5, 0.45)
    sfx = reverb(sfx, 1.8, 0.2, semilla=4)
    mus /= np.max(np.abs(mus)) + 1e-9
    sfx /= np.max(np.abs(sfx)) + 1e-9
    fade = np.minimum(1, np.minimum(t_all / 1.5, (total - t_all) / 4))
    return mus * fade, sfx * fade


# --------------------------------------------------------------------------
# Principal
# --------------------------------------------------------------------------


def main():
    escenas = ESCENAS
    if PRUEBA:
        escenas = [ESCENAS[int(i) - 1] for i in PRUEBA.split(",")]
    todos = [f for e in escenas for f in e["voz"]] + LEYENDA_VOZ
    print("Narración...", flush=True)
    clips = narrar(todos)
    clips_esc, i = [], 0
    for e in escenas:
        clips_esc.append(clips[i:i + len(e["voz"])])
        i += len(e["voz"])
    clips_ley = clips[i:]

    INTRO = 7.0 if not PRUEBA else 0.0
    plan = []
    t = INTRO - (FUNDIDO if INTRO else 0)
    for e, cl in zip(escenas, clips_esc):
        subs, tt = [], 1.0
        for txt, c in zip(e["voz"], cl):
            subs.append((tt, len(c) / SR, txt))
            tt += len(c) / SR + 0.55
        dur = max(8.0, tt + 1.4)
        plan.append((e, t, dur, subs))
        t += dur - FUNDIDO
    leyenda_ini = t + FUNDIDO
    subs_ley, tt = [], 2.5
    for txt, c in zip(LEYENDA_VOZ, clips_ley):
        subs_ley.append((tt, len(c) / SR, txt))
        tt += len(c) / SR + 0.8
    total = leyenda_ini + tt + 4.5
    print(f"Duración: {total:.1f}s", flush=True)

    # audio
    voz = np.zeros(int(total * SR) + SR)
    for (e, t0, dur, subs), cl in zip(plan, clips_esc):
        for (ts, _, _), c in zip(subs, cl):
            a = int((t0 + ts) * SR)
            voz[a:a + len(c)] += c
    for (ts, _, _), c in zip(subs_ley, clips_ley):
        a = int((leyenda_ini + ts) * SR)
        voz[a:a + len(c)] += c
    voz = reverb(voz, 1.4, 0.14, semilla=3)
    mus, sfx = banda_sonora(len(voz) / SR, plan, INTRO, leyenda_ini)
    env_v = np.convolve(np.abs(voz), np.ones(SR // 8) / (SR // 8), mode="same")
    duck = 1 - 0.5 * np.clip(env_v * 7, 0, 1)
    mezcla = voz * 0.95 + mus * 0.34 * duck + sfx * 0.3 * (1 - 0.35 * np.clip(env_v * 7, 0, 1))
    mezcla /= max(1.0, np.max(np.abs(mezcla)) / 0.97)
    sf.write(TMP_WAV, mezcla.astype(np.float32), SR)

    # recursos visuales
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    viñ = np.clip(1.1 - 0.5 * r ** 2.3, 0.3, 1.0).astype(np.float32)[..., None]
    rnd = np.random.default_rng(5)
    granos = [cv2.resize(rnd.normal(0, 7, (H // 2, W // 2)).astype(np.float32), (W, H))[..., None] for _ in range(8)]
    niebla = [ruido_tileable(W // 2, H // 2, 1, 30), ruido_tileable(W // 2, H // 2, 2, 55)]

    f_sub = fuente(F_SUB, 38, b"Medium")
    subs_cache = {}

    def sub_img(txt):
        if txt not in subs_cache:
            subs_cache[txt] = texto_img(envolver(txt, f_sub, 1550), f_sub, (245, 240, 230, 255), 4, 1.25)
        return subs_cache[txt]

    caps = {}
    for e, _, _, _ in plan:
        c1, c2 = e["cap"]
        caps[e["img"]] = (texto_img(c1, fuente(F_TITULO, 46, b"Bold"), ORO + (255,), 5, tracking=6) if c1 else None,
                          texto_img(c2.upper(), fuente(F_SUB, 26, b"Regular"), (225, 215, 195, 255), 4, tracking=4))
    t_tit = texto_img("APOCALIPSIS", fuente(F_TITULO, 190, b"Bold"), (236, 196, 110, 255), 12, tracking=18)
    t_tit_glow = cv2.GaussianBlur(t_tit, (0, 0), 18)
    t_sub = texto_img("Las visiones del fin de los tiempos", fuente(F_SUB, 48, b"Regular"), (230, 220, 200, 255), 6)
    f_ley = fuente(F_SUB, 50, b"Regular")
    t_ley = [texto_img(l, f_ley, (238, 230, 214, 255), 6) for l in LEYENDA]
    t_ref = texto_img(LEYENDA_REF, fuente(F_TITULO, 40, b"Bold"), ORO + (255,), 5, tracking=8)
    t_ao = texto_img("Α   Ω", fuente(F_GRIEGO, 120), ORO + (255,), 10)

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", TMP_WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-tune", "film",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    cache = {}

    def escena(i):
        if i not in cache:
            if len(cache) > 2:
                cache.pop(min(cache))
            cache[i] = Escena(plan[i][0], i)
        return cache[i]

    polvo_negro = Escena.__new__(Escena)
    polvo_negro.pp = np.random.default_rng(77).random((160, 5)).astype(np.float32)

    def brasas_negro(fr, t, n=90):
        for x, y, v, f, rr in polvo_negro.pp[:n].tolist():
            xx = (x * W + 40 * math.sin(t * 1.2 + f * 9)) % W
            yy = (y * H - t * (40 + 80 * v)) % H
            a = 0.5 + 0.4 * math.sin(t * 5 + f * 20)
            cv2.circle(fr, (int(xx), int(yy)), int(1 + rr * 2.2), (230 * a, (110 + 80 * v) * a, 30 * a), -1,
                       cv2.LINE_AA)

    n_total = int(total * FPS)
    for fi in range(n_total):
        t = fi / FPS
        activos = [(i, e, t0, d, s) for i, (e, t0, d, s) in enumerate(plan) if t0 <= t < t0 + d]
        fr = np.zeros((H, W, 3), np.float32)
        if activos:
            i, e, t0, d, s = activos[-1]
            fr = escena(i).cuadro(t - t0, d, niebla)
            if len(activos) > 1:
                ia, ea, ta, da, _ = activos[0]
                prev = escena(ia).cuadro(t - ta, da, niebla)
                u = min(1, (t - t0) / FUNDIDO)
                u = u * u * (3 - 2 * u)
                fr = prev * (1 - u) + fr * u
            elif INTRO and t < t0 + FUNDIDO and i == 0:
                fr *= min(1, (t - t0) / FUNDIDO)
            elif t > t0 + d - FUNDIDO and i == len(plan) - 1:
                fr *= max(0, (t0 + d - t) / FUNDIDO)
        # título
        if t < INTRO:
            brasas_negro(fr, t)
            a = min(1, max(0, (t - 1.0) / 2.0)) * min(1, max(0, (INTRO - FUNDIDO - t) / 1.0))
            gx = W / 2 - t_tit.shape[1] / 2
            pegar(fr, t_tit_glow * np.array([1, 0.55, 0.2, 0.9], np.float32), gx, H / 2 - 150, a)
            pegar(fr, t_tit, gx, H / 2 - 150, a)
            a2 = min(1, max(0, (t - 2.6) / 1.5)) * min(1, max(0, (INTRO - FUNDIDO - t) / 1.0))
            pegar(fr, t_sub, W / 2 - t_sub.shape[1] / 2, H / 2 + 70, a2)
        # leyenda final
        if t >= leyenda_ini - 0.5:
            tl = t - leyenda_ini
            brasas_negro(fr, t, 60)
            fin = min(1, max(0, (total - 1.5 - t) / 2.0))
            y0 = H / 2 - 230
            for k, im in enumerate(t_ley):
                a = min(1, max(0, (tl - 1.0 - k * 1.2) / 1.5)) * fin
                pegar(fr, im, W / 2 - im.shape[1] / 2, y0 + k * 72, a)
            a = min(1, max(0, (tl - 6.5) / 1.5)) * fin
            pegar(fr, t_ref, W / 2 - t_ref.shape[1] / 2, y0 + 4 * 72 + 30, a)
            a = min(1, max(0, (tl - 9.0) / 2.0)) * fin
            pegar(fr, t_ao, W / 2 - t_ao.shape[1] / 2, y0 + 4 * 72 + 120, a)

        # acabado
        fr = fr * viñ + granos[fi % len(granos)]
        fr[:BARRA] = 0
        fr[H - BARRA:] = 0
        # rótulos de capítulo y subtítulos
        for i, e, t0, d, s in activos:
            tl = t - t0
            c1, c2 = caps[e["img"]]
            a = min(1, max(0, (tl - 1.2) / 0.8)) * min(1, max(0, (4.8 - tl) / 0.8))
            if c1 is not None:
                pegar(fr, c1, 80, BARRA + 30, a)
                pegar(fr, c2, 84, BARRA + 30 + c1.shape[0] - 38, a)
            elif a > 0:
                pegar(fr, c2, 84, BARRA + 40, a)
            for ts, dd, txt in s:
                q = tl - ts
                if -0.2 <= q < dd + 0.35:
                    im = sub_img(txt)
                    a = min(1, (q + 0.2) / 0.3, (dd + 0.35 - q) / 0.3)
                    pegar(fr, im, W / 2 - im.shape[1] / 2, H - BARRA / 2 - im.shape[0] / 2 + 4, max(0, a))
        if t >= leyenda_ini:
            for ts, dd, txt in subs_ley:
                pass  # la leyenda ya se muestra en pantalla
        if t < 0.8:
            fr *= t / 0.8
        proc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if fi % 300 == 0:
            print(f"{fi}/{n_total}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(TMP_WAV)
    print("Listo:", OUT, flush=True)


if __name__ == "__main__":
    main()
