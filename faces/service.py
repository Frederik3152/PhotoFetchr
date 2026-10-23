"""The faces service PhotoFetchr calls during upload.

    POST /analyze   image file -> faces with boxes and suggested people
    POST /index     image file + picture_id (+ assignments) -> faces stored for a saved photo
    GET  /health

Holds the face model (~750 MB) in one process. PhotoFetchr treats it as optional: if
this service is down, uploads work as before, just without suggestions.

Dev:  uv run gunicorn -b 0.0.0.0:8901 -w 1 --threads 2 service:app
"""
import json
import threading
from io import BytesIO

from flask import Flask, jsonify, request
from PIL import Image

from common import FACE_MODEL, connect, face_model, faces_in, upright
from suggest import assign, candidates, likelihood, load_calibration

# Below this calibrated likelihood a suggestion is shown as unsure ("Ida?").
UNSURE_BELOW = 0.8

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024
model = face_model()
model_lock = threading.Lock()
calibration = load_calibration()


def read_image():
    file = request.files.get("photo")
    if file is None:
        return None
    img = Image.open(BytesIO(file.read()))
    img.draft("RGB", (1600, 1600))
    img = upright(img).convert("RGB")
    img.thumbnail((1600, 1600))
    return img


def detect(img):
    with model_lock:
        return faces_in(model, img)


@app.get("/health")
def health():
    return {"ok": True, "model": FACE_MODEL, "threshold": calibration["threshold"]}


@app.post("/analyze")
def analyze():
    img = read_image()
    if img is None:
        return jsonify(error="send the image as form field 'photo'"), 400
    found = detect(img)
    with connect() as db:
        per_face = [candidates(db, emb) for _, _, emb in found]
        chosen = assign(per_face, calibration["threshold"])
        ids = [c[0] for c in chosen if c]
        names = dict(db.execute("SELECT id, name FROM photofetchr.people WHERE id = ANY(%s)", (ids,)).fetchall())
    faces = []
    for (box, score, _), pick in zip(found, chosen):
        face = {"box": [round(v, 4) for v in box], "det_score": round(score, 3), "person": None}
        if pick:
            p = likelihood(calibration, pick[1])
            face["person"] = {"id": pick[0], "name": names.get(pick[0]), "similarity": round(pick[1], 3),
                              "likelihood": round(p, 2), "unsure": p < UNSURE_BELOW}
        faces.append(face)
    return {"faces": faces}


@app.post("/index")
def index():
    """Store a saved photo's faces. `assignments` maps face index -> person id for the faces
    whose person the uploader confirmed; those become reference faces."""
    img = read_image()
    picture_id = request.form.get("picture_id", type=int)
    if img is None or picture_id is None:
        return jsonify(error="send 'photo' and 'picture_id'"), 400
    assignments = {int(k): int(v) for k, v in json.loads(request.form.get("assignments") or "{}").items()}
    found = detect(img)
    with connect() as db:
        db.execute("DELETE FROM photofetchr.faces WHERE picture_id = %s AND model = %s", (picture_id, FACE_MODEL))
        for i, (box, score, emb) in enumerate(found):
            db.execute(
                "INSERT INTO photofetchr.faces (picture_id, model, box, det_score, embedding, person_id) "
                "VALUES (%s, %s, %s, %s, %s::vector, %s)",
                (picture_id, FACE_MODEL, box, score, emb.tolist(), assignments.get(i)))
        db.execute(
            "INSERT INTO photofetchr.face_scans (picture_id, model, face_count) VALUES (%s, %s, %s) "
            "ON CONFLICT (picture_id, model) DO UPDATE SET face_count = EXCLUDED.face_count, scanned_at = now()",
            (picture_id, FACE_MODEL, len(found)))
    return {"picture_id": picture_id, "faces": len(found),
            "references_added": sum(1 for i in range(len(found)) if i in assignments)}
