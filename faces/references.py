"""Build and calibrate the reference set: the "training" for people suggestions.

    uv run references.py mark         mark reference faces from existing tags
    uv run references.py calibrate    measure accuracy, write calibration.json

`mark` only writes `faces.person_id`, and only where the tags leave no doubt: the photo is
tagged with exactly one person and exactly one face was detected in it. Existing
PhotoFetchr tables are only read.

`calibrate` tests every reference face against all the others, excluding references
from the same day: those are often near-identical shots, and a new upload usually comes
from a new day. It fits how often a suggestion is right as a smooth curve over similarity
(a logistic regression), which the upload page shows as the match percentage.
"""
import json
import sys
from datetime import datetime, timezone

import numpy as np

from common import FACE_MODEL, connect
from suggest import CALIBRATION_FILE

BIN = 0.05
# Suggest a person only where the fitted curve says the suggestion is right at least this
# often...
MIN_LIKELIHOOD = 0.5
# ...and never below this similarity. Calibration only contains people who have
# references, but uploads also contain strangers; with this model, faces of two different
# people rarely score above it. An assumption, to be checked against real uploads.
STRANGER_FLOOR = 0.35


def mark():
    with connect() as db:
        n = db.execute("""
            UPDATE photofetchr.faces f SET person_id = t.peopleid
            FROM photofetchr.face_scans s,
                 (SELECT pictureid, min(peopleid) AS peopleid FROM photofetchr.person_picture
                  GROUP BY pictureid HAVING count(*) = 1) t
            WHERE s.picture_id = f.picture_id AND s.model = f.model AND s.face_count = 1
              AND t.pictureid = f.picture_id AND f.model = %s AND f.person_id IS NULL
        """, (FACE_MODEL,)).rowcount
        total, people = db.execute(
            "SELECT count(*), count(DISTINCT person_id) FROM photofetchr.faces WHERE person_id IS NOT NULL"
        ).fetchone()
    print(f"marked {n} new reference faces; {total} references for {people} people")


def fit_logistic(x, y, steps=50):
    """Fit P(y) = 1 / (1 + exp(-(a + b x))) by Newton's method; returns (a, b)."""
    X = np.column_stack([np.ones_like(x, dtype=float), x.astype(float)])
    w = np.zeros(2)
    for _ in range(steps):
        p = 1 / (1 + np.exp(-X @ w))
        grad = X.T @ (y - p)
        hess = X.T @ (X * (p * (1 - p))[:, None]) + 1e-6 * np.eye(2)
        w += np.linalg.solve(hess, grad)
    return w[0], w[1]


def calibrate():
    with connect() as db:
        rows = db.execute("""
            SELECT f.person_id, p.photo_taken, f.embedding::text
            FROM photofetchr.faces f JOIN photofetchr.pictures p ON p.id = f.picture_id
            WHERE f.person_id IS NOT NULL AND f.model = %s
        """, (FACE_MODEL,)).fetchall()
    people = np.array([r[0] for r in rows])
    days = np.array([str(r[1]) for r in rows])
    emb = np.array([json.loads(r[2]) for r in rows], dtype=np.float32)
    sim = emb @ emb.T
    sim[days[:, None] == days[None, :]] = -1  # never match within the same day (or itself)

    # The suggestion is the person of the nearest reference face on another day.
    nn = sim.argmax(axis=1)
    best_sim = sim[np.arange(len(sim)), nn]
    best_person = np.where(best_sim > -0.5, people[nn], -1)
    correct = best_person == people

    # Only faces whose person has references on other days can be matched at all.
    matchable = np.array([((people == p) & (days != d)).any() for p, d in zip(people, days)])
    print(f"{len(rows)} reference faces, {len(set(people))} people, "
          f"{matchable.sum()} with a reference of the same person on another day\n")

    a, b = fit_logistic(best_sim[matchable], correct[matchable])
    curve = lambda x: 1 / (1 + np.exp(-(a + b * x)))
    threshold = round(max(STRANGER_FLOOR, (np.log(MIN_LIKELIHOOD / (1 - MIN_LIKELIHOOD)) - a) / b), 3)

    print(" similarity   suggested   coverage   right in this band       fitted")
    lo = 0.10
    while lo < 0.80:
        at_or_above = matchable & (best_sim >= lo)
        band = matchable & (best_sim >= lo) & (best_sim < lo + BIN)
        band_prec = f"{correct[band].mean():6.1%} ({band.sum():3d})" if band.any() else "     -       "
        print(f"   >= {lo:.2f}     {at_or_above.sum():6d}     {at_or_above.sum() / matchable.sum():6.0%}     "
              f"{band_prec}       {curve(lo + BIN / 2):6.1%}")
        lo += BIN
    shown = matchable & (best_sim >= threshold)
    print(f"\nat the threshold {threshold}: suggestions for {shown.sum() / matchable.sum():.0%} of faces, "
          f"{correct[shown].mean():.1%} of them right")

    calibration = {
        "model": FACE_MODEL,
        "threshold": float(threshold),
        "logistic": {"intercept": round(float(a), 4), "slope": round(float(b), 4)},
        "references": int(len(rows)),
        "people": int(len(set(people))),
        "method": "nearest reference per person, references from the same day excluded; "
                  "likelihood = 1 / (1 + exp(-(intercept + slope * similarity)))",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calibration, f, indent=1)
    print(f"wrote {CALIBRATION_FILE}")


if __name__ == "__main__":
    {"mark": mark, "calibrate": calibrate}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
