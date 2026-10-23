"""Copy prod pictures' metadata (never the images) into dev.

    uv run subset.py references     every photo tagged with exactly one person
    uv run subset.py sample [N]     a fixed mix of N photos (default 200) for quick tests

`references` is what the reference set is built from. `sample` takes up to PER_PERSON
single-person photos per person, then fills up with untagged and group photos. Both are
deterministic. Existing dev rows are left alone.
"""
import sys

from common import DEV_DSN, PROD_DSN, connect

PER_PERSON = 8

SINGLE = """
    SELECT pictureid, min(peopleid) AS peopleid
    FROM photofetchr.person_picture GROUP BY pictureid HAVING count(*) = 1
"""

REFERENCES = f"SELECT pictureid FROM ({SINGLE}) single"

SAMPLE = f"""
WITH single AS ({SINGLE}), per_person AS (
    SELECT pictureid, row_number() OVER (PARTITION BY peopleid ORDER BY md5(pictureid::text)) AS rn
    FROM single
), chosen AS (
    SELECT pictureid AS id FROM per_person WHERE rn <= %(per_person)s
)
SELECT id FROM chosen
UNION ALL
(SELECT p.id FROM photofetchr.pictures p
 WHERE p.id NOT IN (SELECT pictureid FROM single)
 ORDER BY md5(p.id::text)
 LIMIT greatest(%(size)s - (SELECT count(*) FROM chosen), 0))
"""


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "references":
        query, params = REFERENCES, {}
    elif mode == "sample":
        query, params = SAMPLE, {"per_person": PER_PERSON, "size": int(sys.argv[2]) if len(sys.argv) > 2 else 200}
    else:
        sys.exit(__doc__)

    with connect(PROD_DSN) as prod:
        ids = [r[0] for r in prod.execute(query, params)]
        pictures = prod.execute(
            "SELECT id, file_name, country, photo_taken, file_path, thumbnail_path, file_size "
            "FROM photofetchr.pictures WHERE id = ANY(%s)", (ids,)).fetchall()
        tags = prod.execute(
            "SELECT peopleid, pictureid FROM photofetchr.person_picture WHERE pictureid = ANY(%s)",
            (ids,)).fetchall()

    with connect(DEV_DSN) as dev, dev.cursor() as cur:
        cur.executemany(
            "INSERT INTO photofetchr.pictures "
            "(id, file_name, country, photo_taken, file_path, thumbnail_path, file_size) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING", pictures)
        cur.executemany(
            "INSERT INTO photofetchr.person_picture (peopleid, pictureid) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING", tags)
        total = cur.execute("SELECT count(*) FROM photofetchr.pictures").fetchone()[0]
    print(f"{mode}: {len(ids)} pictures, {len(tags)} person tags; dev now has {total} pictures")


if __name__ == "__main__":
    main()
