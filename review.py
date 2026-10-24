# Temporary: a one-off review of the faces in existing photos, to grow the set of
# reference faces people suggestions are made from. Switched on with ENABLE_FACE_REVIEW=1
# (see app.py); delete this file and templates/review.html when the review is done.
#
# Two groups of photos, in this order:
#   1. tagged with one person, with two or more faces: which face is the tagged person?
#   2. tagged with two or more people: which face is who?
# Each face is pre-matched to the people tagged on the photo where its nearest reference
# faces agree; saving stores the faces' people, adds a tag when a face is named as someone
# the photo isn't tagged with yet, and marks the photo reviewed.
#
# /review-faces/misc/ is a second pass over the photos tagged "Misc. Friends", which isn't one
# person and so can't be a reference: its faces are opened up to be named again, and saving
# removes the Misc. Friends tag and any face still marked as it. A photo leaves that queue
# once saved.
import os
from contextlib import contextmanager
from io import BytesIO

import psycopg2
import requests
from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, url_for
from PIL import Image

from config import config
from imaging import upright

review = Blueprint('review', __name__, url_prefix='/review-faces')
db_config = config()

FACE_MODEL = 'insightface-buffalo_l'
NEIGHBOURS = 20
# A face is pre-matched to a person tagged on the photo from this similarity up; lower than
# the upload page's threshold because the choice is narrowed to the photo's own tags
TAGGED_MIN = 0.25
# ...and to someone not tagged on the photo only from the upload page's threshold up
UNTAGGED_MIN = 0.35
MISC_NAME = 'Misc. Friends'
# Dev only: where to fetch images whose file isn't on this machine
PHOTOS_FALLBACK_URL = os.environ.get('PHOTOS_FALLBACK_URL')

# The photos to review, as (group, picture id), in review order
QUEUE = """
    WITH tags AS (
        SELECT pictureid, count(*) AS n FROM photofetchr.person_picture GROUP BY pictureid
    )
    SELECT CASE WHEN t.n = 1 THEN 1 ELSE 2 END AS grp, s.picture_id, s.reviewed_at IS NOT NULL AS done
    FROM photofetchr.face_scans s JOIN tags t ON t.pictureid = s.picture_id
    WHERE s.model = %(model)s AND s.face_count >= 1 AND (t.n >= 2 OR s.face_count >= 2)
"""


@contextmanager
def cursor():
    """A cursor in one transaction, committed on success; the connection is closed after."""
    conn = psycopg2.connect(**db_config)
    try:
        with conn, conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def misc_id(cur):
    cur.execute("SELECT id FROM photofetchr.people WHERE name = %s", (MISC_NAME,))
    row = cur.fetchone()
    return row[0] if row else None


def next_misc(cur, misc, after=None):
    """The next photo still tagged Misc. Friends, after the given picture id when given."""
    cur.execute("""
        SELECT pictureid FROM photofetchr.person_picture
        WHERE peopleid = %s AND pictureid > %s ORDER BY pictureid LIMIT 1
    """, (misc, after or 0))
    row = cur.fetchone()
    return row[0] if row else None


def next_picture(cur, after=None):
    """The next unreviewed photo in review order, after (group, id) when given."""
    cur.execute(f"""
        SELECT grp, picture_id FROM ({QUEUE}) q
        WHERE NOT done AND (%(after)s::int[] IS NULL OR ARRAY[grp, picture_id] > %(after)s::int[])
        ORDER BY grp, picture_id LIMIT 1
    """, {'model': FACE_MODEL, 'after': list(after) if after else None})
    row = cur.fetchone()
    return row[1] if row else None


def progress(cur):
    cur.execute(f"SELECT grp, count(*), count(*) FILTER (WHERE done) FROM ({QUEUE}) q GROUP BY grp ORDER BY grp",
                {'model': FACE_MODEL})
    names = {1: 'One person tagged, several faces', 2: 'Several people tagged'}
    return [{'group': g, 'name': names[g], 'total': total, 'done': done} for g, total, done in cur.fetchall()]


def prematch(cur, picture_id, faces, tagged, misc=None):
    """For each face without a person: the person it most likely is, or None.

    Faces are matched to the people tagged on the photo first (each person once), then any
    face still open to someone else if the match is as strong as on the upload page.
    """
    cur.execute("""
        SELECT f.id, r.person_id, 1 - (r.embedding <=> f.embedding)
        FROM photofetchr.faces f
        CROSS JOIN LATERAL (
            SELECT person_id, embedding FROM photofetchr.faces r
            WHERE r.person_id IS NOT NULL AND r.person_id IS DISTINCT FROM %(misc)s
              AND r.model = f.model AND r.picture_id <> f.picture_id
            ORDER BY r.embedding <=> f.embedding LIMIT %(k)s
        ) r
        WHERE f.picture_id = %(picture)s AND f.model = %(model)s
          AND (f.person_id IS NULL OR f.person_id = %(misc)s)
    """, {'picture': picture_id, 'model': FACE_MODEL, 'k': NEIGHBOURS, 'misc': misc})
    best = {}  # (face id, person id) -> best similarity
    for face_id, person_id, sim in cur.fetchall():
        key = (face_id, person_id)
        best[key] = max(best.get(key, -1), sim)

    taken = {f['person_id'] for f in faces if f['person_id']}
    out = {}
    for restrict, minimum in ((tagged, TAGGED_MIN), (None, UNTAGGED_MIN)):
        pairs = sorted(((sim, face, person) for (face, person), sim in best.items()
                        if sim >= minimum and (restrict is None or person in restrict)), reverse=True)
        for sim, face, person in pairs:
            if face not in out and person not in taken:
                out[face] = {'person_id': person, 'similarity': round(sim, 3)}
                taken.add(person)
    return out


@review.route('/')
def start():
    with cursor() as cur:
        picture_id = next_picture(cur)
    if picture_id is None:
        return render_template('review.html', photo=None, progress=None, people=[])
    return redirect(url_for('review.photo', picture_id=picture_id))


@review.route('/<int:picture_id>')
def photo(picture_id):
    return show(picture_id, misc_mode=False)


@review.route('/misc/')
def misc_start():
    with cursor() as cur:
        misc = misc_id(cur)
        picture_id = next_misc(cur, misc) if misc else None
    if picture_id is None:
        return render_template('review.html', photo=None, progress=None, people=[])
    return redirect(url_for('review.misc_photo', picture_id=picture_id))


@review.route('/misc/<int:picture_id>')
def misc_photo(picture_id):
    return show(picture_id, misc_mode=True)


def show(picture_id, misc_mode):
    """The review page for one photo. In misc mode, faces marked Misc. Friends are open
    to be named again and Misc. Friends isn't offered or shown as a tag."""
    with cursor() as cur:
        misc = misc_id(cur) if misc_mode else None
        cur.execute("SELECT id, name FROM photofetchr.people WHERE id IS DISTINCT FROM %s ORDER BY name", (misc,))
        people = [{'id': i, 'name': n} for i, n in cur.fetchall()]
        cur.execute("SELECT file_name, photo_taken, country FROM photofetchr.pictures WHERE id = %s", (picture_id,))
        row = cur.fetchone()
        if not row:
            abort(404)
        cur.execute("SELECT peopleid FROM photofetchr.person_picture WHERE pictureid = %s", (picture_id,))
        tagged = {r[0] for r in cur.fetchall()} - {misc}
        cur.execute("""
            SELECT id, box, person_id FROM photofetchr.faces
            WHERE picture_id = %s AND model = %s ORDER BY box[1]
        """, (picture_id, FACE_MODEL))
        faces = [{'id': i, 'box': list(box), 'person_id': None if misc and p == misc else p,
                  'was_misc': bool(misc) and p == misc} for i, box, p in cur.fetchall()]
        matches = prematch(cur, picture_id, faces, tagged, misc)
        for f in faces:
            f['match'] = matches.get(f['id'])
        cur.execute("SELECT reviewed_at IS NOT NULL FROM photofetchr.face_scans WHERE picture_id = %s AND model = %s",
                    (picture_id, FACE_MODEL))
        reviewed = bool((cur.fetchone() or [False])[0])
        if misc_mode:
            cur.execute("SELECT count(*) FROM photofetchr.person_picture WHERE peopleid = %s", (misc,))
            stats = [{'name': f'Photos still tagged {MISC_NAME}', 'left': cur.fetchone()[0]}]
            group = None
        else:
            cur.execute(f"SELECT grp FROM ({QUEUE}) q WHERE picture_id = %(picture)s",
                        {'model': FACE_MODEL, 'picture': picture_id})
            group = (cur.fetchone() or [None])[0]
            stats = progress(cur)

    save_url = url_for('review.misc_save' if misc_mode else 'review.save', picture_id=picture_id)
    photo = {'id': picture_id, 'file_name': row[0], 'date': row[1].isoformat() if row[1] else None,
             'country': row[2], 'tagged': sorted(tagged), 'faces': faces, 'reviewed': reviewed, 'group': group,
             'save_url': save_url, 'misc': misc_mode}
    return render_template('review.html', photo=photo, progress=stats, people=people)


@review.route('/<int:picture_id>/image')
def image(picture_id):
    """The photo upright and at most 1600 px, so the face boxes line up with it."""
    with cursor() as cur:
        cur.execute("SELECT file_path FROM photofetchr.pictures WHERE id = %s", (picture_id,))
        row = cur.fetchone()
    if not row:
        abort(404)
    if row[0] and os.path.exists(row[0]):
        img = Image.open(row[0])
    elif PHOTOS_FALLBACK_URL:
        r = requests.get(f"{PHOTOS_FALLBACK_URL}/image/{picture_id}", timeout=60)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
    else:
        abort(404)
    img.draft('RGB', (1600, 1600))
    img = upright(img).convert('RGB')
    img.thumbnail((1600, 1600))
    out = BytesIO()
    img.save(out, 'JPEG', quality=85)
    return Response(out.getvalue(), content_type='image/jpeg')


@review.route('/<int:picture_id>', methods=['POST'])
def save(picture_id):
    return store(picture_id, misc_mode=False)


@review.route('/misc/<int:picture_id>', methods=['POST'])
def misc_save(picture_id):
    return store(picture_id, misc_mode=True)


def store(picture_id, misc_mode):
    """Store who each face is. Body: {"faces": {face id: person id or null}, "skip": bool}.

    In misc mode this also removes the photo's Misc. Friends tag and clears any face still
    marked as Misc. Friends."""
    body = request.get_json(force=True)
    with cursor() as cur:
        misc = misc_id(cur) if misc_mode else None
        if not misc_mode:
            cur.execute(f"SELECT grp FROM ({QUEUE}) q WHERE picture_id = %(picture)s",
                        {'model': FACE_MODEL, 'picture': picture_id})
            group = (cur.fetchone() or [3])[0]
        if not body.get('skip'):
            chosen = {int(face): (int(person) if person else None) for face, person in body.get('faces', {}).items()}
            if misc and misc in chosen.values():
                return jsonify({'error': f'{MISC_NAME} can\'t be chosen here'}), 400
            cur.execute("""
                SELECT person_id FROM photofetchr.faces
                WHERE picture_id = %s AND model = %s AND person_id IS NOT NULL AND NOT id = ANY(%s)
                  AND person_id IS DISTINCT FROM %s
            """, (picture_id, FACE_MODEL, list(chosen), misc))
            named = [p for p in chosen.values() if p] + [r[0] for r in cur.fetchall()]
            if len(named) != len(set(named)):
                return jsonify({'error': 'The same person is chosen for two faces'}), 400
            named = [p for p in chosen.values() if p]
            for face_id, person_id in chosen.items():
                cur.execute("UPDATE photofetchr.faces SET person_id = %s WHERE id = %s AND picture_id = %s",
                            (person_id, face_id, picture_id))
            # A face named as someone the photo isn't tagged with adds that tag
            for person_id in set(named):
                cur.execute("""
                    INSERT INTO photofetchr.person_picture (peopleid, pictureid) VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (person_id, picture_id))
            if misc:
                cur.execute("UPDATE photofetchr.faces SET person_id = NULL WHERE picture_id = %s AND person_id = %s",
                            (picture_id, misc))
                cur.execute("DELETE FROM photofetchr.person_picture WHERE pictureid = %s AND peopleid = %s",
                            (picture_id, misc))
            cur.execute("UPDATE photofetchr.face_scans SET reviewed_at = now() WHERE picture_id = %s AND model = %s",
                        (picture_id, FACE_MODEL))
        if misc_mode:
            next_id = next_misc(cur, misc, after=picture_id) if misc else None
            done_url, next_url = url_for('review.misc_start'), 'review.misc_photo'
        else:
            next_id = next_picture(cur, after=(group, picture_id))
            done_url, next_url = url_for('review.start'), 'review.photo'
    return jsonify({'next': url_for(next_url, picture_id=next_id) if next_id else done_url})
