"""Video realista estilo pizarra (whiteboard) sobre el futuro de la IA y la robótica.

Una mano real con marcador dibuja cada imagen como boceto a lápiz, luego la imagen
se revela a todo color; los textos se escriben a mano en azul y un narrador explica
cada escena con ejemplos.

Uso:  python3 generar_video.py  ->  futuro_ia_robotica.mp4
Requiere: pillow numpy soundfile kokoro-onnx imageio-ffmpeg
Voz (Kokoro, desde GitHub), ruta en KOKORO_DIR (por defecto ./recursos):
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
Las imágenes de recursos/ se generaron con IA y se ampliaron x4 con superres.py;
la mano se recorta con preparar_mano.py.
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
OUT = os.path.join(AQUI, "futuro_ia_robotica.mp4")
TMP_WAV = os.path.join(AQUI, "_narracion.wav")

W, H, FPS, SR = 1920, 1080, 30, 24000
F_TITULO = os.path.join(REC, "PermanentMarker-Regular.ttf")
F_TEXTO = os.path.join(REC, "Kalam-Bold.ttf")
VOZ = "em_alex"

AZUL = (18, 92, 214)
AZUL_OSC = (12, 60, 160)
TINTA = (35, 38, 48)

ESCALA_MANO = 0.72
PUNTA_MANO = (135, 416)  # punta del marcador en recursos/mano_rgba.png
TRANSICION = 0.6

ESCENAS = [
    dict(titulo="El futuro de la IA y la robótica", imagen="robot.png",
         puntos=["Una revolución que ya comenzó", "Cambiará cómo vivimos, trabajamos e invertimos"],
         voz="¿Cómo será el mundo en los próximos diez años? La inteligencia artificial y la "
             "robótica lo están cambiando todo: cómo vivimos, cómo trabajamos y cómo invertimos. "
             "Y está pasando ahora mismo."),
    dict(titulo="La IA ya piensa", imagen="cerebro.png",
         puntos=["Razona, escribe y programa", "Ej: crea una app en minutos",
                 "Ej: resume 100 páginas en segundos"],
         voz="Hoy la inteligencia artificial ya razona, escribe y programa. Por ejemplo, puede "
             "crear una aplicación completa en minutos, o resumir un informe de cien páginas en "
             "segundos. Lo que a una persona le tomaría semanas."),
    dict(titulo="Robots humanoides", imagen="fabrica.png",
         puntos=["Trabajan junto a los humanos", "Ej: ensamblan autos 24/7",
                 "Pronto en hogares y hospitales"],
         voz="Los robots humanoides ya trabajan junto a las personas. En las fábricas, por ejemplo, "
             "ensamblan piezas de autos las veinticuatro horas, sin cansarse. Y muy pronto los "
             "veremos también en hogares y hospitales."),
    dict(titulo="Medicina del futuro", imagen="cirugia.png",
         puntos=["Diagnóstico temprano con IA", "Ej: detecta un cáncer en una radiografía",
                 "Cirugía robótica milimétrica"],
         voz="En la medicina, la inteligencia artificial puede detectar un cáncer en una radiografía "
             "antes que el ojo humano. Y los robots quirúrgicos operan con precisión milimétrica: "
             "menos dolor y recuperaciones más rápidas."),
    dict(titulo="Trading e inversión", imagen="trading.png",
         puntos=["Algoritmos que analizan 24/7", "Ej: millones de datos por segundo",
                 "Datos + disciplina = ventaja"],
         voz="En los mercados financieros, los algoritmos analizan millones de datos por segundo y "
             "operan sin miedo ni avaricia. Para un trader, la ventaja ya no es la suerte. Es la "
             "información, y sobre todo, la disciplina."),
    dict(titulo="El nuevo trabajo", imagen="handshake.png",
         puntos=["Humanos + IA = equipo", "La IA no te reemplaza...", "te reemplaza quien sepa usarla"],
         voz="Muchos trabajos van a cambiar, y nacerán profesiones que hoy ni imaginamos. Pero "
             "recuerda esto: la inteligencia artificial no te va a reemplazar. Te va a reemplazar "
             "quien sepa usarla."),
    dict(titulo="El futuro es de quienes se preparan hoy", imagen="ciudad.png",
         puntos=["Aprende", "Adáptate", "Lidera"],
         voz="Ciudades inteligentes, robots en cada esquina y una economía impulsada por la "
             "inteligencia artificial. El futuro no espera a nadie. Pertenece a quienes se preparan "
             "hoy. Aprende. Adáptate. Y lidera."),
    dict(final=True,
         voz="Este video fue creado por Yéison Serrano, máster en inteligencia artificial."),
]

_fuentes = {}


def fuente(ruta, size):
    if (ruta, size) not in _fuentes:
        _fuentes[(ruta, size)] = ImageFont.truetype(ruta, size)
    return _fuentes[(ruta, size)]


# --------------------------------------------------------------------------
# Elementos
# --------------------------------------------------------------------------


class Texto:
    """Texto que se revela de izquierda a derecha mientras la mano lo escribe."""
    mano = True

    def __init__(self, texto, ruta, size, x, y, color=AZUL, centrado=False, vineta=False):
        f = fuente(ruta, size)
        bb = f.getbbox(texto)
        extra = int(size * 0.6) if vineta else 0
        w, h = bb[2] + extra + 12, bb[3] + int(size * 0.3)
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        if vineta:
            r = size * 0.13
            cy = size * 0.66
            d.ellipse([4, cy - r, 4 + 2 * r, cy + r], fill=color)
        d.text((extra, 0), texto, font=f, fill=color)
        self.x = int(x - w / 2) if centrado else int(x)
        self.y = int(y)
        self.size = size
        self.dur = 0.3 + 0.045 * len(texto)

    def dibujar(self, cuadro, p, t):
        w = max(1, int(self.img.width * p))
        cuadro.alpha_composite(self.img.crop((0, 0, w, self.img.height)), (self.x, self.y))
        return (self.x + w, self.y + self.size * (0.62 + 0.22 * math.sin(t * 36)))

    def fijar(self, base):
        base.alpha_composite(self.img, (self.x, self.y))


def boceto_lapiz(img):
    """Convierte una foto en un boceto a lápiz (RGBA, trazos oscuros sobre transparente)."""
    g = img.convert("L")
    inv = ImageChops.invert(g).filter(ImageFilter.GaussianBlur(10))
    ga = np.asarray(g, dtype=np.float32)
    ia = np.asarray(inv, dtype=np.float32)
    dodge = np.clip(ga * 255.0 / np.maximum(1.0, 255.0 - ia), 0, 255)
    oscuridad = np.clip((255.0 - dodge - 20.0) * 1.7, 0, 235)
    sk = Image.new("RGBA", img.size, TINTA + (0,))
    sk.putalpha(Image.fromarray(oscuridad.astype(np.uint8)))
    return sk


class Foto:
    """La mano dibuja la foto como boceto (zigzag) y luego traza un marco azul."""
    mano = True

    def __init__(self, archivo, x, y, w, h):
        foto = Image.open(os.path.join(REC, archivo)).convert("RGB").resize((w, h), Image.LANCZOS)
        foto = foto.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
        self.foto = foto.convert("RGBA")
        self.boceto = boceto_lapiz(foto)
        self.x, self.y, self.w, self.h = x, y, w, h
        self.dur = 3.6
        # recorrido en zigzag que sigue la mano
        banda = 70
        filas = math.ceil(h / banda)
        self.ruta = []
        for i in range(filas + 1):
            yy = min(h, i * banda + banda / 2)
            xs = (0, w) if i % 2 == 0 else (w, 0)
            self.ruta += [(xs[0], yy), (xs[1], yy + banda * 0.5)]
        self.seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(self.ruta, self.ruta[1:])]
        self.largo = sum(self.seg)
        self.mascara = Image.new("L", (w, h), 0)
        self.hecho = 0.0
        m = 14
        self.marco = [(x - m, y - m), (x + w + m, y - m), (x + w + m, y + h + m), (x - m, y + h + m),
                      (x - m, y - m)]
        self.marco_seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(self.marco, self.marco[1:])]

    def _punto(self, ruta, segs, dist):
        acc = 0.0
        for (a, b), s in zip(zip(ruta, ruta[1:]), segs):
            if acc + s >= dist:
                f = (dist - acc) / s if s else 0
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            acc += s
        return ruta[-1]

    def _marco_parcial(self, cuadro, q):
        total = sum(self.marco_seg)
        objetivo = q * total
        d = ImageDraw.Draw(cuadro)
        acc = 0.0
        punta = self.marco[0]
        for (a, b), s in zip(zip(self.marco, self.marco[1:]), self.marco_seg):
            if acc >= objetivo:
                break
            f = min(1.0, (objetivo - acc) / s)
            fin = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            d.line([a, fin], fill=AZUL, width=7)
            d.ellipse([fin[0] - 3.5, fin[1] - 3.5, fin[0] + 3.5, fin[1] + 3.5], fill=AZUL)
            punta = fin
            acc += s
        return punta

    def dibujar(self, cuadro, p, t):
        ps = min(1.0, p / 0.75)
        dist = ps * self.largo
        if dist > self.hecho:
            dm = ImageDraw.Draw(self.mascara)
            n = max(2, int((dist - self.hecho) / 10))
            pts = [self._punto(self.ruta, self.seg, self.hecho + (dist - self.hecho) * k / n) for k in range(n + 1)]
            dm.line(pts, fill=255, width=110, joint="curve")
            self.hecho = dist
        sk = self.boceto.copy()
        sk.putalpha(ImageChops.multiply(self.boceto.getchannel("A"), self.mascara))
        cuadro.alpha_composite(sk, (self.x, self.y))
        if p < 0.75:
            px, py = self._punto(self.ruta, self.seg, dist)
            return (self.x + px, self.y + py)
        return self._marco_parcial(cuadro, (p - 0.75) / 0.25)

    def fijar(self, base):
        base.alpha_composite(self.boceto, (self.x, self.y))
        self._marco_parcial(base, 1.0)


class Revelar:
    """La foto a color aparece sobre el boceto (sin mano)."""
    mano = False

    def __init__(self, foto):
        self.f = foto
        self.dur = 1.4

    def dibujar(self, cuadro, p, t):
        e = p * p * (3 - 2 * p)
        capa = self.f.foto.copy()
        capa.putalpha(int(255 * e))
        cuadro.alpha_composite(capa, (self.f.x, self.f.y))
        return None

    def fijar(self, base):
        base.alpha_composite(self.f.foto, (self.f.x, self.f.y))


class Linea:
    """Subrayado a mano."""
    mano = True

    def __init__(self, x0, x1, y, color=AZUL, grosor=8):
        self.pts = [(x0 + (x1 - x0) * k / 40, y + 6 * math.sin(k / 40 * math.pi)) for k in range(41)]
        self.color, self.grosor = color, grosor
        self.dur = 0.8

    def dibujar(self, cuadro, p, t):
        n = max(2, int(len(self.pts) * p))
        ImageDraw.Draw(cuadro).line(self.pts[:n], fill=self.color, width=self.grosor, joint="curve")
        return self.pts[n - 1]

    def fijar(self, base):
        ImageDraw.Draw(base).line(self.pts, fill=self.color, width=self.grosor, joint="curve")


def envolver(texto, ruta, size, ancho):
    f = fuente(ruta, size)
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if f.getlength(prueba) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    lineas.append(actual)
    return lineas


def construir(esc):
    """Devuelve la lista de (elemento, arranca_con_anterior)."""
    if esc.get("final"):
        return [(Texto("Creado por", F_TEXTO, 80, W / 2, 250, TINTA, centrado=True), False),
                (Texto("JEISSON SERRANO", F_TITULO, 150, W / 2, 360, centrado=True), False),
                (Linea(560, 1360, 590), False),
                (Texto("Máster en Inteligencia Artificial", F_TITULO, 76, W / 2, 650, centrado=True), False)]
    elems = []
    size_t = 92
    while fuente(F_TITULO, size_t).getlength(esc["titulo"]) > 1680:
        size_t -= 4
    elems.append((Texto(esc["titulo"], F_TITULO, size_t, W / 2, 62, centrado=True), False))
    foto = Foto(esc["imagen"], 120, 250, 840, 628)
    elems.append((foto, False))
    elems.append((Revelar(foto), False))
    y = 300
    for i, p in enumerate(esc["puntos"]):
        lineas = envolver(p, F_TEXTO, 60, 760)
        for j, l in enumerate(lineas):
            color = AZUL if not l.startswith("Ej:") else AZUL_OSC
            elems.append((Texto(l, F_TEXTO, 60, 1060 if j == 0 else 1100, y, color, vineta=(j == 0)),
                          i == 0 and j == 0))  # el primer punto arranca junto con el revelado
            y += 82
        y += 40
    return elems


def programar(elems, t0):
    """Asigna tiempos: los elementos con mano van en serie; Revelar se solapa."""
    plan, t, fin_prev = [], t0, t0
    for e, junto in elems:
        if isinstance(e, Revelar):
            plan.append((e, fin_prev, e.dur))
            continue
        inicio = fin_prev + 0.15 if junto else t
        plan.append((e, inicio, e.dur))
        fin_prev = inicio + e.dur
        t = fin_prev + 0.3
    return plan, max(ti + d for _, ti, d in plan)


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------


def narrar():
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin"))
    out = []
    for esc in ESCENAS:
        s, sr = k.create(esc["voz"], voice=VOZ, speed=1.0, lang="es")
        out.append(np.asarray(s, dtype=np.float32))
    return out


def musica(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    acordes = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63],
               [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    da = 4.0
    out = np.zeros(n)
    for i in range(int(dur / da) + 1):
        a0, a1 = int(i * da * SR), min(n, int((i + 1) * da * SR + SR))
        if a0 >= n:
            break
        tt = t[a0:a1] - t[a0]
        env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, da + 1 - tt) / 1.5)
        for f in acordes[i % 4]:
            for det in (0.997, 1.003):
                out[a0:a1] += np.sin(2 * np.pi * f * det * tt) * env
            out[a0:a1] += 0.3 * np.sin(np.pi * f * tt) * env
    out /= np.max(np.abs(out)) + 1e-9
    return out * np.minimum(1, np.minimum(t / 2, (dur - t) / 3)) * 0.06


def roce_marcador(dur, activo):
    """Sonido suave de marcador sobre la pizarra mientras la mano dibuja."""
    n = int(dur * SR)
    rnd = np.random.default_rng(3)
    ruido = rnd.standard_normal(n)
    # filtro pasa-banda simple (diferencia de medias móviles)
    k1, k2 = 6, 40
    c = np.cumsum(np.insert(ruido, 0, 0))
    m1 = (c[k1:] - c[:-k1]) / k1
    m2 = (c[k2:] - c[:-k2]) / k2
    bp = m1[: len(m2)] - m2
    bp = np.pad(bp, (0, n - len(bp)))
    t = np.arange(n) / SR
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * 7 * t) ** 2
    env = np.interp(t, np.arange(len(activo)) / FPS, activo)
    return bp / (np.max(np.abs(bp)) + 1e-9) * mod * env * 0.05


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------


def cargar_fondo():
    pz = Image.open(os.path.join(REC, "pizarra.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    rnd = np.random.default_rng(1)
    grano = rnd.normal(0, 2.2, (H, W, 1))
    arr = np.clip(np.asarray(pz, dtype=np.float32) + grano, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")


def cargar_mano():
    m = Image.open(os.path.join(REC, "mano_rgba.png"))
    m = m.resize((int(m.width * ESCALA_MANO), int(m.height * ESCALA_MANO)), Image.LANCZOS)
    sombra = Image.new("L", m.size, 0)
    sombra.paste(m.getchannel("A").point(lambda a: int(a * 0.28)))
    sombra = sombra.filter(ImageFilter.GaussianBlur(16))
    return m, sombra, (PUNTA_MANO[0] * ESCALA_MANO, PUNTA_MANO[1] * ESCALA_MANO)


def main():
    print("Narración...")
    clips = narrar()
    fondo = cargar_fondo()
    mano, sombra, off = cargar_mano()

    escenas = []
    for esc, clip in zip(ESCENAS, clips):
        elems = construir(esc)
        plan, fin_dibujo = programar(elems, TRANSICION + 0.1)
        dur_voz = TRANSICION + 0.3 + len(clip) / SR
        dur = max(dur_voz, fin_dibujo) + 1.2
        if esc.get("final"):
            dur += 1.5
        escenas.append((plan, dur))
    total = sum(d for _, d in escenas)
    print(f"Duración total: {total:.1f}s")

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", TMP_WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", OUT]

    # Primera pasada: sólo se calcula cuándo dibuja la mano (para el sonido del marcador)
    activo = []
    for plan, dur in escenas:
        for f in range(int(round(dur * FPS))):
            t = f / FPS
            activo.append(1.0 if any(e.mano and ti <= t < ti + d for e, ti, d in plan) else 0.0)
    activo = np.convolve(np.array(activo), np.ones(3) / 3, mode="same")

    audio = np.zeros(int(total * SR) + SR)
    t0 = 0.0
    for clip, (_, dur) in zip(clips, escenas):
        a = int((t0 + TRANSICION + 0.3) * SR)
        audio[a:a + len(clip)] += clip / (np.max(np.abs(clip)) + 1e-9) * 0.9
        t0 += dur
    dur_audio = len(audio) / SR
    audio += musica(dur_audio)
    audio += roce_marcador(dur_audio, activo)
    sf.write(TMP_WAV, np.clip(audio, -1, 1).astype(np.float32), SR)

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    pos = [W + 400.0, H + 500.0]
    anterior = None
    g = 0
    for idx, (plan, dur) in enumerate(escenas):
        print(f"Escena {idx + 1}/{len(escenas)} ({dur:.1f}s)")
        base = fondo.copy()
        fijados = set()
        n = int(round(dur * FPS))
        for f in range(n):
            t = f / FPS
            cuadro = None
            punta = None
            for j, (e, ti, d) in enumerate(plan):
                if j in fijados or t < ti:
                    continue
                p = min(1.0, (t - ti) / d)
                if p >= 1.0:
                    e.fijar(base)
                    fijados.add(j)
                    continue
                if cuadro is None:
                    cuadro = base.copy()
                pt = e.dibujar(cuadro, p, t)
                if e.mano and pt is not None:
                    punta = pt
            if cuadro is None:
                cuadro = base.copy()

            # zoom lento de cámara
            z = 1.0 + 0.025 * (t / dur)
            if z > 1.001:
                cw, ch = W / z, H / z
                cuadro = cuadro.crop((int((W - cw) / 2), int((H - ch) / 2),
                                      int((W + cw) / 2), int((H + ch) / 2))).resize((W, H), Image.BILINEAR)
                if punta is not None:
                    punta = ((punta[0] - W / 2) * z + W / 2, (punta[1] - H / 2) * z + H / 2)

            if punta is not None and t >= TRANSICION:
                dist = math.hypot(punta[0] - pos[0], punta[1] - pos[1])
                if dist > 30:
                    pos[0] += (punta[0] - pos[0]) * 0.5
                    pos[1] += (punta[1] - pos[1]) * 0.5
                else:
                    pos = [punta[0], punta[1]]
            else:
                pos[0] += (W + 400 - pos[0]) * 0.15
                pos[1] += (H + 500 - pos[1]) * 0.15
            hx, hy = int(pos[0] - off[0]), int(pos[1] - off[1])
            if hx < W and hy < H:
                cuadro.paste((0, 0, 0, 255), (hx + 28, hy + 34), sombra)
                cuadro.paste(mano, (hx, hy), mano)
            rgb = cuadro.convert("RGB")

            # transición: el contenido anterior se borra (fundido a pizarra limpia)
            if anterior is not None and t < TRANSICION:
                u = t / TRANSICION
                rgb = Image.blend(anterior, rgb, u * u * (3 - 2 * u))
            if g < int(0.6 * FPS):
                rgb = Image.blend(Image.new("RGB", (W, H)), rgb, g / (0.6 * FPS))
            proc.stdin.write(rgb.tobytes())
            g += 1
        anterior = rgb
    proc.stdin.close()
    proc.wait()
    os.remove(TMP_WAV)
    print("Listo:", OUT)


if __name__ == "__main__":
    main()
