-- PhotoFetchr's core tables. Photo files live on disk (see "Storage Structure" in the
-- README); these hold their metadata and who is in them. The face tables for people
-- suggestions are in faces/schema.sql.

CREATE SCHEMA IF NOT EXISTS photofetchr;

-- One row per photo. file_path and thumbnail_path are absolute paths under /photos.
CREATE TABLE IF NOT EXISTS photofetchr.pictures (
    id              serial  PRIMARY KEY,
    file_name       text,
    country         text,
    photo_taken     date,
    file_path       text,
    thumbnail_path  text,
    file_size       bigint
);
CREATE INDEX IF NOT EXISTS idx_picture_filename ON photofetchr.pictures (file_name);
CREATE INDEX IF NOT EXISTS idx_pictures_file_path ON photofetchr.pictures (file_path);

-- The people photos can be tagged with. Added by hand, with an explicit id.
CREATE TABLE IF NOT EXISTS photofetchr.people (
    id        integer PRIMARY KEY,
    name      text,
    alias     text,
    birthday  date
);
CREATE INDEX IF NOT EXISTS idx_people_name ON photofetchr.people (name);

-- Who is in which photo.
CREATE TABLE IF NOT EXISTS photofetchr.person_picture (
    peopleid   integer NOT NULL REFERENCES photofetchr.people(id),
    pictureid  integer NOT NULL REFERENCES photofetchr.pictures(id),
    PRIMARY KEY (peopleid, pictureid)
);
