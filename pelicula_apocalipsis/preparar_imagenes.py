"""Prepara las imágenes de la película: amplía, restaura rostros y calcula profundidad.

Para cada imagen de recursos/originales/:
  1. Amplía con Real-ESRGAN hasta >= 2880 px de ancho (superres.py).
  2. Detecta rostros (YOLOFace) y los restaura con GFPGAN 1.4.
  3. Calcula un mapa de profundidad (MiDaS small) para el movimiento 2.5D.
Salida: recursos/listas/<nombre>.jpg y recursos/listas/<nombre>_prof.png

Uso: python3 preparar_imagenes.py [nombres...]
Modelos (variable MODELOS, por defecto ./modelos):
  RealESRGAN_x4plus.pth  https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.1.0
  yoloface_8n.onnx, gfpgan_1.4.onnx  https://github.com/facefusion/facefusion-assets/releases/tag/models-3.0.0
  model-small.onnx  https://github.com/isl-org/MiDaS/releases/tag/v2_1
"""
import glob
import os
import sys

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

import superres

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELOS = os.environ.get("MODELOS", os.path.join(AQUI, "modelos"))
ORIG = os.path.join(AQUI, "recursos", "originales")
LISTAS = os.path.join(AQUI, "recursos", "listas")
ANCHO_MIN = 2880
ANCHO_MAX = 3400

# plantilla de 5 puntos (ojos, nariz, comisuras) para alinear a 512x512 (FFHQ)
PLANTILLA = np.array([[0.37691676, 0.46864664], [0.62285697, 0.46912813], [0.50123859, 0.61331904],
                      [0.39308822, 0.72541100], [0.61150205, 0.72490465]], dtype=np.float32) * 512


def sesion(nombre):
    return ort.InferenceSession(os.path.join(MODELOS, nombre), providers=["CPUExecutionProvider"])


def detectar_rostros(det, img_rgb, umbral=0.55):
    h, w = img_rgb.shape[:2]
    esc = min(640 / w, 640 / h)
    rw, rh = int(w * esc), int(h * esc)
    lienzo = np.zeros((640, 640, 3), dtype=np.float32)
    lienzo[:rh, :rw] = cv2.resize(img_rgb[:, :, ::-1], (rw, rh)) / 255.0  # BGR, [0,1]
    x = lienzo.transpose(2, 0, 1)[None]
    out = np.squeeze(det.run(None, {"input": x})[0]).T  # (8400, 20)
    caja, puntaje, puntos = out[:, :4], out[:, 4], out[:, 5:]
    ok = puntaje > umbral
    caja, puntaje, puntos = caja[ok], puntaje[ok], puntos[ok]
    if not len(caja):
        return []
    cajas = np.stack([caja[:, 0] - caja[:, 2] / 2, caja[:, 1] - caja[:, 3] / 2,
                      caja[:, 0] + caja[:, 2] / 2, caja[:, 1] + caja[:, 3] / 2], axis=1) / esc
    lm = np.stack([puntos[:, 0::3], puntos[:, 1::3]], axis=2) / esc  # (n, 5, 2)
    idx = cv2.dnn.NMSBoxes([[float(a), float(b), float(c - a), float(d - b)] for a, b, c, d in cajas],
                           puntaje.tolist(), umbral, 0.4)
    idx = np.array(idx).flatten() if len(idx) else []
    return [(cajas[i], lm[i], float(puntaje[i])) for i in idx]


def restaurar_rostros(det, gfp, img_rgb):
    rostros = detectar_rostros(det, img_rgb)
    res = img_rgb.astype(np.float32)
    n = 0
    for caja, lm, sc in rostros:
        tam = max(caja[2] - caja[0], caja[3] - caja[1])
        if tam < 48:
            continue
        M, _ = cv2.estimateAffinePartial2D(lm.astype(np.float32), PLANTILLA, method=cv2.LMEDS)
        if M is None:
            continue
        rec = cv2.warpAffine(img_rgb, M, (512, 512), borderMode=cv2.BORDER_REPLICATE)
        x = ((rec.astype(np.float32) / 255.0 - 0.5) / 0.5).transpose(2, 0, 1)[None]
        y = gfp.run(None, {"input": x})[0][0]
        y = ((np.clip(y, -1, 1) + 1) / 2 * 255).transpose(1, 2, 0)
        # máscara suave del rostro en el espacio alineado
        m = np.zeros((512, 512), dtype=np.float32)
        cv2.rectangle(m, (40, 40), (472, 490), 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), 28)
        Mi = cv2.invertAffineTransform(M)
        h, w = img_rgb.shape[:2]
        y_img = cv2.warpAffine(y, Mi, (w, h), borderMode=cv2.BORDER_REPLICATE)
        m_img = cv2.warpAffine(m, Mi, (w, h))[..., None] * 0.85
        res = res * (1 - m_img) + y_img * m_img
        n += 1
    return np.clip(res, 0, 255).astype(np.uint8), n


def profundidad(midas, img_rgb):
    x = cv2.resize(img_rgb, (256, 256), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    d = midas.run(None, {"0": x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    d = (d - d.min()) / (d.max() - d.min() + 1e-6)
    h, w = img_rgb.shape[:2]
    d = cv2.resize(d, (w // 4, h // 4), interpolation=cv2.INTER_CUBIC)
    d = cv2.GaussianBlur(d, (0, 0), 3)
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(d, 0, 1)


def main():
    os.makedirs(LISTAS, exist_ok=True)
    nombres = sys.argv[1:] or sorted(os.path.splitext(os.path.basename(p))[0]
                                     for p in glob.glob(os.path.join(ORIG, "*")))
    modelo_sr = None
    det, gfp, midas = sesion("yoloface_8n.onnx"), sesion("gfpgan_1.4.onnx"), sesion("model-small.onnx")
    for nombre in nombres:
        ruta = [p for p in glob.glob(os.path.join(ORIG, nombre + ".*"))][0]
        im = np.asarray(Image.open(ruta).convert("RGB"), dtype=np.float32) / 255.0
        while im.shape[1] < ANCHO_MIN:
            if modelo_sr is None:
                modelo_sr = ort.InferenceSession(
                    superres.construir_onnx(superres.cargar_pth(os.path.join(MODELOS, "RealESRGAN_x4plus.pth")))
                    .SerializeToString(), providers=["CPUExecutionProvider"])
            im = np.clip(superres.ampliar(modelo_sr, im), 0, 1)
        img = (im * 255 + 0.5).astype(np.uint8)
        if img.shape[1] > ANCHO_MAX:
            img = cv2.resize(img, (ANCHO_MAX, int(img.shape[0] * ANCHO_MAX / img.shape[1])),
                             interpolation=cv2.INTER_AREA)
        img, n = restaurar_rostros(det, gfp, img)
        d = profundidad(midas, img)
        Image.fromarray(img).save(os.path.join(LISTAS, nombre + ".jpg"), quality=93)
        Image.fromarray((d * 65535).astype(np.uint16)).save(os.path.join(LISTAS, nombre + "_prof.png"))
        print(f"{nombre}: {img.shape[1]}x{img.shape[0]}, {n} rostro(s) restaurado(s)", flush=True)


if __name__ == "__main__":
    main()
