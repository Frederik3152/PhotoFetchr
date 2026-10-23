"""Evaluate the prototype against what's already tagged in PhotoFetchr.

    uv run evaluate.py faces        leave-one-out person identification
    uv run evaluate.py facesheet    review page: every face, its match and the tags
"""
import html
import json
import os
import sys

import numpy as np

from common import FACE_MODEL, PHOTOFETCHR_URL, connect

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
def faces():
    """Ground truth: photos with exactly one tagged person and exactly one detected face."""
    with connect() as db:
        rows = db.execute("""
            SELECT f.embedding::text, pp.peopleid
            FROM photofetchr.faces f
            JOIN photofetchr.face_scans s ON s.picture_id = f.picture_id AND s.model = f.model
            JOIN photofetchr.person_picture pp ON pp.pictureid = f.picture_id
            WHERE f.model = %s AND s.face_count = 1
              AND (SELECT count(*) FROM photofetchr.person_picture x WHERE x.pictureid = f.picture_id) = 1
        """, (FACE_MODEL,)).fetchall()
    emb = np.array([json.loads(e) for e, _ in rows], dtype=np.float32)
    people = np.array([p for _, p in rows])
    print(f"{len(rows)} labelled faces, {len(set(people))} people")

    sim = emb @ emb.T  # embeddings are L2-normalised, so this is cosine similarity
    np.fill_diagonal(sim, -1)
    # Only faces whose person appears at least twice can be matched at all.
    counts = {p: (people == p).sum() for p in set(people)}
    usable = np.array([counts[p] > 1 for p in people])
    nn = sim.argmax(axis=1)
    best = sim[np.arange(len(sim)), nn]
    correct = people[nn] == people

    print(f"{usable.sum()} faces have another face of the same person to match against")
    print("similarity  suggested  of usable  correct  precision")
    for t in (0.0, 0.2, 0.3, 0.4, 0.5):
        m = usable & (best >= t)
        prec = correct[m].mean() if m.any() else float("nan")
        print(f"  >= {t:.1f}     {m.sum():5d}     {m.sum() / usable.sum():6.0%}   {correct[m].sum():5d}    {prec:6.0%}")


THRESHOLD = 0.2


def load_faces():
    """Every detected face, which of them are ground truth, and each one's best match.

    Ground truth is a face that is the only one in a photo tagged with exactly one person.
    Every face is matched against the ground-truth faces (never itself), which is how the
    app would suggest a person.
    """
    with connect() as db:
        faces = db.execute("""
            SELECT f.id, f.picture_id, f.box, f.embedding::text, s.face_count
            FROM photofetchr.faces f
            JOIN photofetchr.face_scans s ON s.picture_id = f.picture_id AND s.model = f.model
            WHERE f.model = %s ORDER BY f.id
        """, (FACE_MODEL,)).fetchall()
        tags = {}
        for pic, person in db.execute("SELECT pictureid, peopleid FROM photofetchr.person_picture"):
            tags.setdefault(pic, set()).add(person)
        names = dict(db.execute("SELECT id, coalesce(alias, name) FROM photofetchr.people"))

    emb = np.array([json.loads(f[3]) for f in faces], dtype=np.float32)
    truth = np.array([f[4] == 1 and len(tags.get(f[1], ())) == 1 for f in faces])
    label = np.array([next(iter(tags[f[1]])) if t else -1 for f, t in zip(faces, truth)])

    sim = emb @ emb[truth].T
    gt_index = np.flatnonzero(truth)
    sim[gt_index, np.arange(len(gt_index))] = -1  # a ground-truth face can't match itself
    nn = sim.argmax(axis=1)
    out = []
    for i, f in enumerate(faces):
        j = gt_index[nn[i]]
        out.append({
            "face_id": f[0], "picture_id": f[1], "box": f[2],
            "truth": bool(truth[i]), "person": int(label[i]) if truth[i] else None,
            "photo_tags": sorted(tags.get(f[1], ())),
            "match_face_id": faces[j][0], "match_picture_id": faces[j][1], "match_box": faces[j][2],
            "suggested": int(label[j]), "similarity": float(sim[i, nn[i]]),
        })
    return out, names


def face_sheet():
    faces, names = load_faces()
    name = lambda p: html.escape(names.get(p, f"#{p}"))

    def crop(pid, box):
        return (f"<canvas width=96 height=96 data-src='{PHOTOFETCHR_URL}/image/{pid}' "
                f"data-box='{','.join(f'{v:.4f}' for v in box)}'></canvas>")

    def row(f, verdict):
        tags = ", ".join(name(p) for p in f["photo_tags"]) or "none"
        return (f"<tr class={verdict}><td>{crop(f['picture_id'], f['box'])}<br>"
                f"<a href='{PHOTOFETCHR_URL}/image/{f['picture_id']}'>#{f['picture_id']}</a></td>"
                f"<td>{crop(f['match_picture_id'], f['match_box'])}<br>"
                f"<a href='{PHOTOFETCHR_URL}/image/{f['match_picture_id']}'>#{f['match_picture_id']}</a></td>"
                f"<td><b>{name(f['suggested'])}</b><br>similarity {f['similarity']:.2f}</td>"
                f"<td>{tags}</td><td>{verdict.replace('-', ' ')}</td></tr>")

    truth = [f for f in faces if f["truth"]]
    rest = [f for f in faces if not f["truth"]]

    def truth_verdict(f):
        if f["similarity"] < THRESHOLD:
            return "below-threshold"
        return "correct" if f["suggested"] == f["person"] else "wrong"

    def rest_verdict(f):
        if f["similarity"] < THRESHOLD:
            return "below-threshold"
        if not f["photo_tags"]:
            return "photo-untagged"
        return "among-tags" if f["suggested"] in f["photo_tags"] else "not-among-tags"

    order = {"wrong": 0, "not-among-tags": 0, "below-threshold": 1, "photo-untagged": 2, "correct": 3, "among-tags": 3}
    sections = [
        ("Ground truth: the only face in a photo tagged with one person",
         "Each face is matched against all other ground-truth faces. Mistakes first, then "
         "faces with no match above the threshold, then correct ones.", truth, truth_verdict),
        ("All other faces: group photos, untagged photos, and photos where the face count "
         "doesn't match the tags", "The real use case. The person is unknown, but if the photo "
         "is tagged, the suggestion should be one of its tags.", rest, rest_verdict),
    ]
    parts = ["<!doctype html><meta charset=utf-8><title>PhotoFetchr face prototype</title>",
             "<style>body{font:14px system-ui;margin:16px;background:#111;color:#ddd}"
             "table{border-collapse:collapse}td,th{padding:6px 10px;border-bottom:1px solid #333;"
             "vertical-align:top;text-align:left}canvas{background:#222;border-radius:4px}"
             "a{color:#8ab4f8;font-size:12px}tr.wrong,tr.not-among-tags{background:#3a1d1d}"
             "tr.below-threshold{color:#888}tr.correct td:last-child,tr.among-tags td:last-child{color:#7c7}</style>",
             f"<h1>Face suggestions: {len(faces)} faces in 212 photos</h1>",
             f"<p>Threshold: similarity ≥ {THRESHOLD}. Click a photo number to open the original.</p>"]
    for title, blurb, group, verdict_of in sections:
        verdicts = [verdict_of(f) for f in group]
        summary = ", ".join(f"{verdicts.count(v)} {v.replace('-', ' ')}" for v in dict.fromkeys(sorted(verdicts, key=order.get)))
        parts.append(f"<h2>{html.escape(title)}</h2><p>{html.escape(blurb)}<br><b>{summary}</b></p>")
        parts.append("<table><tr><th>face</th><th>best match</th><th>suggests</th>"
                     "<th>tagged in this photo</th><th>verdict</th></tr>")
        for f, v in sorted(zip(group, verdicts), key=lambda fv: (order[fv[1]], -fv[0]["similarity"])):
            parts.append(row(f, v))
        parts.append("</table>")
    # Crop each face out of the original once it scrolls into view. Browsers apply EXIF
    # rotation to <img>, which matches the rotated image the boxes were measured on.
    parts.append("""<script>
const draw = c => { const [x1,y1,x2,y2] = c.dataset.box.split(',').map(Number), img = new Image();
  img.onload = () => { const w = img.naturalWidth, h = img.naturalHeight, pad = 0.15,
      bw = (x2-x1)*w, bh = (y2-y1)*h, s = Math.max(bw, bh)*(1+2*pad),
      cx = (x1+x2)/2*w, cy = (y1+y2)/2*h;
    c.getContext('2d').drawImage(img, cx-s/2, cy-s/2, s, s, 0, 0, c.width, c.height); };
  img.src = c.dataset.src; };
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); draw(e.target); } }), {rootMargin: '400px'});
document.querySelectorAll('canvas[data-src]').forEach(c => io.observe(c));
</script>""")
    path = os.path.join(OUT, "faces.html")
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(parts))
    for title, _, group, verdict_of in sections:
        verdicts = [verdict_of(f) for f in group]
        print(f"{title.split(':')[0]}: " + ", ".join(f"{verdicts.count(v)} {v}" for v in dict.fromkeys(sorted(verdicts, key=order.get))))
    print(f"wrote {path}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "faces":
        faces()
    elif cmd == "facesheet":
        face_sheet()
    else:
        sys.exit(__doc__)
