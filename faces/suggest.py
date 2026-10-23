"""Turning a face embedding into a suggested person.

A face is compared with the reference faces (faces with a person_id). Each person scores
the similarity of their closest reference face; the best-scoring person is the
suggestion. Within one photo, a person is suggested for at most one face.
"""
import json
import math
import os

from common import FACE_MODEL

NEIGHBOURS = 20
# The calibration made from this repo's dev data ships next to the code. A deployment
# keeps its own on a volume (FACES_CALIBRATION), so a rebuilt image doesn't lose it.
BUNDLED_CALIBRATION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")
CALIBRATION_FILE = os.environ.get("FACES_CALIBRATION", BUNDLED_CALIBRATION)


def rank_people(neighbours):
    """[(person_id, similarity)] sorted best first -> each person once, with their best score."""
    best = {}
    for person_id, sim in neighbours:
        best.setdefault(person_id, sim)
    return sorted(best.items(), key=lambda kv: -kv[1])


def candidates(db, embedding):
    """The people closest to one face embedding, best first, as [(person_id, similarity)]."""
    vec = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
    rows = db.execute("""
        SELECT person_id, 1 - (embedding <=> %(v)s::vector)
        FROM photofetchr.faces
        WHERE person_id IS NOT NULL AND model = %(model)s
        ORDER BY embedding <=> %(v)s::vector
        LIMIT %(k)s
    """, {"v": vec, "model": FACE_MODEL, "k": NEIGHBOURS}).fetchall()
    return rank_people(rows)


def assign(per_face, threshold):
    """Pick one person per face, each person at most once per photo, strongest pairs first.

    per_face: for each face, its [(person_id, similarity)]. Returns, per face,
    (person_id, similarity) or None when nobody clears the threshold.
    """
    pairs = sorted(((sim, i, pid) for i, cands in enumerate(per_face) for pid, sim in cands if sim >= threshold),
                   reverse=True)
    out, used = [None] * len(per_face), set()
    for sim, i, pid in pairs:
        if out[i] is None and pid not in used:
            out[i] = (pid, sim)
            used.add(pid)
    return out


def load_calibration():
    path = CALIBRATION_FILE if os.path.exists(CALIBRATION_FILE) else BUNDLED_CALIBRATION
    with open(path) as f:
        return json.load(f)


def likelihood(calibration, similarity):
    """How often a suggestion at this similarity is right, 0-1, from the fitted curve."""
    fit = calibration["logistic"]
    return 1 / (1 + math.exp(-(fit["intercept"] + fit["slope"] * similarity)))
