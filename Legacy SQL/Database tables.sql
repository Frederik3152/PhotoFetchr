-- The following tables, relationships and indices form the basis of the database used for PhotoFetchr

-- Create the pictures table in the pi_data schema and its primary key id
CREATE TABLE IF NOT EXISTS pi_data.pictures
(
    id integer NOT NULL DEFAULT nextval('pi_data."pictures_PhotoID_seq"'::regclass),
    file_name text,
    content bytea,
    country text,
    photo_taken date,
    CONSTRAINT pictures_pkey PRIMARY KEY (id)
)

-- Create a btree index on the file_name column
CREATE INDEX IF NOT EXISTS idx_picture_filename
    ON pi_data.pictures USING btree
    (file_name COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;

-- Create a btree index on the picture_id column
CREATE INDEX IF NOT EXISTS idx_picture_id
    ON pi_data.pictures USING btree
    (id ASC NULLS LAST)
    TABLESPACE pg_default;

-- Create the people table in the pi_data schema and its primary key id
CREATE TABLE IF NOT EXISTS pi_data.people
(
    id integer NOT NULL,
    name text COLLATE pg_catalog."default",
    alias text COLLATE pg_catalog."default",
    birthday date,
    CONSTRAINT people_pkey PRIMARY KEY (id)
)

-- Create an index on the names in the people table
CREATE INDEX IF NOT EXISTS idx_people_name
    ON pi_data.people USING btree
    (name COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;

-- Create the person_picture table in the pi_data schema and sets up the foreign keys
CREATE TABLE IF NOT EXISTS pi_data.person_picture
(
    peopleid integer NOT NULL,
    pictureid integer NOT NULL,
    CONSTRAINT person_picture_pkey PRIMARY KEY (peopleid, pictureid),
    CONSTRAINT person_picture_peopleid_fkey FOREIGN KEY (peopleid)
        REFERENCES pi_data.people (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT person_picture_pictureid_fkey FOREIGN KEY (pictureid)
        REFERENCES pi_data.pictures (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)