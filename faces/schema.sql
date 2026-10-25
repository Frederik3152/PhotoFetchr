-- Face tables for PhotoFetchr. Needs pgvector in the `extensions` schema, which the
-- database's search_path includes (see services/postgresql.md in the homelab vault).

-- Which pictures the face pass has seen, so a picture with no faces isn't scanned again.
-- `reviewed_at` was set by the one-off review of existing photos' faces (October 2026).
CREATE TABLE IF NOT EXISTS photofetchr.face_scans (
    picture_id   integer     NOT NULL REFERENCES photofetchr.pictures(id) ON DELETE CASCADE,
    model        text        NOT NULL,
    face_count   integer     NOT NULL,
    scanned_at   timestamptz NOT NULL DEFAULT now(),
    reviewed_at  timestamptz,
    PRIMARY KEY (picture_id, model)
);

-- One row per detected face. `box` is x1, y1, x2, y2 as fractions of the image turned the
-- way its EXIF orientation says. `person_id` is a confirmed identity, and faces with one
-- are the reference set suggestions are made from.
CREATE TABLE IF NOT EXISTS photofetchr.faces (
    id          serial      PRIMARY KEY,
    picture_id  integer     NOT NULL REFERENCES photofetchr.pictures(id) ON DELETE CASCADE,
    model       text        NOT NULL,
    box         real[]      NOT NULL,
    det_score   real        NOT NULL,
    embedding   vector(512) NOT NULL,
    person_id   integer     REFERENCES photofetchr.people(id),
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS faces_picture_id_idx ON photofetchr.faces (picture_id);
