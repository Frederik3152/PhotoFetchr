"""Shared helpers: database connections, image loading and the face model."""
import os
import time
from io import BytesIO

import numpy as np
import onnxruntime as ort
import psycopg
import requests
from PIL import Image, ImageOps

# libpq service names or full DSNs. Prod is only ever read from.
DEV_DSN = os.environ.get("PHOTOFETCHR_DSN", "service=homelab-dev")
PROD_DSN = os.environ.get("PHOTOFETCHR_PROD_DSN", "service=homelab-prod")
# Where to fetch originals when /photos isn't mounted locally (the dev container).
PHOTOFETCHR_URL = os.environ.get("PHOTOFETCHR_URL", "http://192.168.8.92:5001")
THREADS = int(os.environ.get("EMBED_THREADS", os.cpu_count() or 4))

FACE_MODEL = "insightface-buffalo_l"

ort.set_default_logger_severity(3)


def connect(dsn=DEV_DSN):
    return psycopg.connect(dsn)


def load_image(picture_id, file_path, max_side=1600):
    """Return the picture as an upright RGB PIL image, at most `max_side` px on its long edge.

    Reads the file when the photo store is mounted here, otherwise asks PhotoFetchr for it.
    """
    if file_path and os.path.exists(file_path):
        img = Image.open(file_path)
    else:
        r = requests.get(f"{PHOTOFETCHR_URL}/image/{picture_id}", timeout=60)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
    img.draft("RGB", (max_side, max_side))  # lets the JPEG decoder skip full resolution
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side))
    return img


def face_model():
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import model_zoo

    # Without explicit thread counts onnxruntime pins its threads to cores, which an LXC
    # refuses, and it logs an error per session.
    base_init = model_zoo.PickableInferenceSession.__init__

    def init(self, model_path, **kwargs):
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = THREADS
        opts.inter_op_num_threads = 1
        kwargs.setdefault("sess_options", opts)
        base_init(self, model_path, **kwargs)

    model_zoo.PickableInferenceSession.__init__ = init
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"],
                       allowed_modules=["detection", "recognition"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    return app


def faces_in(app, img, min_score=0.6):
    """Detect faces in a PIL image: list of (box as fractions, det_score, 512-d embedding)."""
    bgr = np.asarray(img)[:, :, ::-1]
    w, h = img.size
    out = []
    for f in app.get(bgr):
        if f.det_score < min_score:
            continue
        x1, y1, x2, y2 = f.bbox
        box = [float(v) for v in (max(0.0, x1 / w), max(0.0, y1 / h), min(1.0, x2 / w), min(1.0, y2 / h))]
        out.append((box, float(f.det_score), f.normed_embedding.astype(np.float32)))
    return out


class Timer:
    def __init__(self):
        self.totals = {}

    def __call__(self, key):
        timer = self

        class _Span:
            def __enter__(self):
                self.t = time.perf_counter()

            def __exit__(self, *exc):
                timer.totals[key] = timer.totals.get(key, 0.0) + time.perf_counter() - self.t

        return _Span()
