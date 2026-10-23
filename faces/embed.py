"""Detect faces and compute face embeddings for pictures the face pass hasn't seen yet.

    uv run embed.py [--limit N]

Needs about 750 MB of memory. On the dev container run it under a memory cap, see
~/.claude/CLAUDE.md.
"""
import argparse
import resource

from common import FACE_MODEL, Timer, connect, face_model, faces_in, load_image


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    args = p.parse_args()

    timer = Timer()
    with timer("load model"):
        app = face_model()

    with connect() as db:
        todo = db.execute("""
            SELECT p.id, p.file_path FROM photofetchr.pictures p
            WHERE NOT EXISTS (SELECT 1 FROM photofetchr.face_scans s
                              WHERE s.picture_id = p.id AND s.model = %s)
            ORDER BY p.id LIMIT %s
        """, (FACE_MODEL, args.limit)).fetchall()

        found, failed = 0, []
        for n, (picture_id, file_path) in enumerate(todo, 1):
            # A photo that can't be read is skipped without a face_scans row, so the next
            # run tries it again.
            try:
                with timer("fetch + decode"):
                    img = load_image(picture_id, file_path)
            except Exception as e:
                failed.append(picture_id)
                print(f"skipped picture {picture_id}: {e}", flush=True)
                continue
            with timer("detect + embed"):
                detected = faces_in(app, img)
            found += len(detected)
            db.execute("DELETE FROM photofetchr.faces WHERE picture_id = %s AND model = %s",
                       (picture_id, FACE_MODEL))
            for box, score, emb in detected:
                db.execute(
                    "INSERT INTO photofetchr.faces (picture_id, model, box, det_score, embedding) "
                    "VALUES (%s, %s, %s, %s, %s::vector)",
                    (picture_id, FACE_MODEL, box, score, emb.tolist()))
            db.execute(
                "INSERT INTO photofetchr.face_scans (picture_id, model, face_count) VALUES (%s, %s, %s) "
                "ON CONFLICT (picture_id, model) DO UPDATE SET face_count = EXCLUDED.face_count, "
                "scanned_at = now()", (picture_id, FACE_MODEL, len(detected)))
            db.commit()
            if n % 25 == 0 or n == len(todo):
                print(f"{n}/{len(todo)} pictures, {found} faces", flush=True)
        if failed:
            print(f"{len(failed)} pictures could not be read: {failed}")

    print("\nseconds per picture:" if todo else "nothing to do")
    for key, total in timer.totals.items():
        per = total if key == "load model" or not todo else total / len(todo)
        print(f"  {key:<16} {per:6.2f}{'  (once)' if key == 'load model' else ''}")
    print(f"peak memory: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MB")


if __name__ == "__main__":
    main()
