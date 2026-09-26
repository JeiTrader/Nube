"""Amplía imágenes x4 con Real-ESRGAN (RRDBNet) sin PyTorch.

Lee los pesos .pth directamente del zip, construye el grafo ONNX y lo ejecuta
con onnxruntime.

Uso: python3 superres.py RealESRGAN_x4plus.pth entrada.jpg salida.png [...]
"""
import io
import pickle
import sys
import zipfile

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto, helper, numpy_helper
from PIL import Image


def cargar_pth(ruta):
    z = zipfile.ZipFile(ruta)
    raiz = z.namelist()[0].split("/")[0]

    class _Storage:
        def __init__(self, dtype):
            self.dtype = dtype

    def rebuild(storage, offset, size, stride, *args):
        flat = storage[offset:]
        return np.lib.stride_tricks.as_strided(
            flat, shape=size, strides=[st * flat.itemsize for st in stride]).copy()

    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if mod == "torch._utils" and name == "_rebuild_tensor_v2":
                return rebuild
            if mod == "torch" and name.endswith("Storage"):
                return _Storage(np.float32 if name == "FloatStorage" else np.float16)
            if mod == "collections" and name == "OrderedDict":
                import collections
                return collections.OrderedDict
            return super().find_class(mod, name)

        def persistent_load(self, pid):
            _, st, key, _, _ = pid
            data = z.read(f"{raiz}/data/{key}")
            return np.frombuffer(data, dtype=st.dtype)

    obj = U(io.BytesIO(z.read(f"{raiz}/data.pkl"))).load()
    return obj.get("params_ema", obj.get("params", obj))


def construir_onnx(p):
    nodos, inits = [], []
    cont = [0]

    def nombre(pref):
        cont[0] += 1
        return f"{pref}_{cont[0]}"

    def conv(x, clave):
        w, b = clave + ".weight", clave + ".bias"
        for k in (w, b):
            if not any(i.name == k for i in inits):
                inits.append(numpy_helper.from_array(p[k].astype(np.float32), k))
        y = nombre("conv")
        nodos.append(helper.make_node("Conv", [x, w, b], [y], pads=[1, 1, 1, 1]))
        return y

    def lrelu(x):
        y = nombre("lr")
        nodos.append(helper.make_node("LeakyRelu", [x], [y], alpha=0.2))
        return y

    def const(v):
        k = nombre("c")
        inits.append(numpy_helper.from_array(np.array(v, dtype=np.float32), k))
        return k

    c02 = const(0.2)

    def op(t, *xs, **kw):
        y = nombre(t.lower())
        nodos.append(helper.make_node(t, list(xs), [y], **kw))
        return y

    def rdb(x, pre):
        x1 = lrelu(conv(x, pre + ".conv1"))
        x2 = lrelu(conv(op("Concat", x, x1, axis=1), pre + ".conv2"))
        x3 = lrelu(conv(op("Concat", x, x1, x2, axis=1), pre + ".conv3"))
        x4 = lrelu(conv(op("Concat", x, x1, x2, x3, axis=1), pre + ".conv4"))
        x5 = conv(op("Concat", x, x1, x2, x3, x4, axis=1), pre + ".conv5")
        return op("Add", op("Mul", x5, c02), x)

    n_bloques = 1 + max(int(k.split(".")[1]) for k in p if k.startswith("body."))
    feat = conv("entrada", "conv_first")
    h = feat
    for i in range(n_bloques):
        pre = f"body.{i}"
        o = rdb(rdb(rdb(h, pre + ".rdb1"), pre + ".rdb2"), pre + ".rdb3")
        h = op("Add", op("Mul", o, c02), h)
    feat = op("Add", feat, conv(h, "conv_body"))
    escalas = const([1.0, 1.0, 2.0, 2.0])
    for k in ("conv_up1", "conv_up2"):
        up = op("Resize", feat, "", escalas, mode="nearest")
        feat = lrelu(conv(up, k))
    salida = conv(lrelu(conv(feat, "conv_hr")), "conv_last")
    nodos.append(helper.make_node("Identity", [salida], ["salida"]))
    g = helper.make_graph(
        nodos, "rrdbnet",
        [helper.make_tensor_value_info("entrada", TensorProto.FLOAT, [1, 3, None, None])],
        [helper.make_tensor_value_info("salida", TensorProto.FLOAT, [1, 3, None, None])],
        inits)
    return helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)], ir_version=8)


def main():
    pth, *pares = sys.argv[1:]
    modelo = construir_onnx(cargar_pth(pth))
    ses = ort.InferenceSession(modelo.SerializeToString(), providers=["CPUExecutionProvider"])
    for ent, sal in zip(pares[::2], pares[1::2]):
        im = np.asarray(Image.open(ent).convert("RGB"), dtype=np.float32) / 255.0
        x = im.transpose(2, 0, 1)[None]
        y = ses.run(None, {"entrada": x})[0][0]
        out = (np.clip(y.transpose(1, 2, 0), 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(out).save(sal)
        print(ent, "->", sal, out.shape)


if __name__ == "__main__":
    main()
