# Deploying people suggestions to prod

The faces service runs as its own container next to PhotoFetchr, in the same compose
project on app-deployment-vm. PhotoFetchr only talks to it when `FACES_URL` is set, and
works as before (without suggestions) whenever the faces container is down.

Do the steps in order. Each one leaves PhotoFetchr working, so you can stop between them.

## 1. Deploy the new PhotoFetchr code

Merge the `embeddings` branch into `main` and push. The n8n deploy flow pulls and rebuilds
as usual. Without `FACES_URL`, the new upload page works with dates read from each photo
but no people suggestions.

## 2. Database (on database-vm, as postgres)

`postgresql-17-pgvector` is already installed: dev uses the same server. Pick a password
for the faces service's own database user first (step 3 needs the same one):

```sh
openssl rand -base64 24
```

Then run `sudo -u postgres psql -d home_database_prod` and paste this, with the password
filled in:

```sql
BEGIN;

-- pgvector in a shared schema, the same as dev (see services/postgresql.md in the vault)
CREATE SCHEMA IF NOT EXISTS extensions;
GRANT USAGE ON SCHEMA extensions TO PUBLIC;
CREATE EXTENSION IF NOT EXISTS vector SCHEMA extensions;
ALTER DATABASE home_database_prod SET search_path = "$user", public, extensions;
SET search_path = "$user", public, extensions;

-- The two new tables, owned by frederik like the rest of photofetchr (faces/schema.sql)
SET ROLE frederik;
CREATE TABLE photofetchr.face_scans (
    picture_id   integer     NOT NULL REFERENCES photofetchr.pictures(id) ON DELETE CASCADE,
    model        text        NOT NULL,
    face_count   integer     NOT NULL,
    scanned_at   timestamptz NOT NULL DEFAULT now(),
    reviewed_at  timestamptz,
    PRIMARY KEY (picture_id, model)
);
CREATE TABLE photofetchr.faces (
    id          serial      PRIMARY KEY,
    picture_id  integer     NOT NULL REFERENCES photofetchr.pictures(id) ON DELETE CASCADE,
    model       text        NOT NULL,
    box         real[]      NOT NULL,
    det_score   real        NOT NULL,
    embedding   vector(512) NOT NULL,
    person_id   integer     REFERENCES photofetchr.people(id),
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX faces_picture_id_idx ON photofetchr.faces (picture_id);
RESET ROLE;

-- The faces service's own user: reads photos and people, writes only the two face tables
CREATE ROLE photofetchr_faces LOGIN PASSWORD '<the password>';
GRANT CONNECT ON DATABASE home_database_prod TO photofetchr_faces;
GRANT USAGE ON SCHEMA photofetchr TO photofetchr_faces;
GRANT SELECT ON photofetchr.pictures, photofetchr.people, photofetchr.person_picture TO photofetchr_faces;
GRANT SELECT, INSERT, UPDATE, DELETE ON photofetchr.faces, photofetchr.face_scans TO photofetchr_faces;
GRANT USAGE ON SEQUENCE photofetchr.faces_id_seq TO photofetchr_faces;

COMMIT;
```

## 3. Compose (on app-deployment-vm, in /home/frederik/projects)

The service's database login, readable only by you:

```sh
cat > faces.env <<'EOF'
PHOTOFETCHR_DSN=host=192.168.8.90 dbname=home_database_prod user=photofetchr_faces password=<the password>
EOF
chmod 600 faces.env
```

In `docker-compose.yml`, add the `faces` service, `FACES_URL` on the PhotoFetchr service,
and the two volumes:

```yaml
services:
  faces:
    build: ./PhotoFetchr/faces
    container_name: photofetchr-faces
    restart: unless-stopped
    env_file: ./faces.env
    environment:
      FACES_CALIBRATION: /data/calibration.json
    volumes:
      - /photos:/photos:ro                  # the scan reads originals; never writes
      - faces-models:/root/.insightface     # the face model, downloaded on first start
      - faces-data:/data                    # prod's calibration
    mem_limit: 1536m
    # No ports: only PhotoFetchr calls it, over the compose network

  photofetchr:
    # ...as it is now, plus:
    environment:
      FACES_URL: http://faces:8901

volumes:
  faces-models:
  faces-data:
```

Then build it. The first build takes a few minutes (it compiles part of insightface):

```sh
docker compose build faces
```

## 4. Build the reference set from the originals

Check that about 1.5 GB of memory is free (`free -m`, the *available* column). The scan
reads all ~6,600 originals and takes roughly 30–60 minutes, so run it as a detached
container that doesn't depend on your SSH session:

```sh
docker compose run -d --name faces-scan faces python embed.py
docker logs -f faces-scan        # Ctrl+C stops watching, not the scan
```

It is done when the log ends with `peak memory:`. Photos it can't read are listed just
before that, and tried again on the next run; `embed.py` can be stopped and started again
and carries on where it left off. Then remove the finished container (keep its log first
if you want it: `docker logs faces-scan > faces-scan.log`) and build the reference set:

```sh
docker rm faces-scan
docker compose run --rm faces python references.py mark
docker compose run --rm faces python references.py calibrate
```

`docker rm` only deletes the stopped container and its log. The results are already in
the database, and the image, the model and the calibration are kept.

## 5. Switch it on

The faces service may already be running (the deploy's `docker compose up -d --build`
starts every service), but it reads the calibration only when it starts, so restart it:

```sh
docker compose restart faces
docker compose up -d photofetchr     # recreates it if FACES_URL isn't applied yet
docker compose exec faces cat /data/calibration.json
docker compose exec photofetchr python -c "import requests; print(requests.get('http://faces:8901/health').json())"
```

`calibration.json` should show today's `created` date and prod's number of references.
The last line should print `{'model': 'insightface-buffalo_l', 'ok': True, 'threshold': ...}`.
Upload a photo to check that people are suggested.

## Turning it off again

- Suggestions only: `docker compose stop faces`. PhotoFetchr carries on without them.
- Completely: remove the `faces` service and `FACES_URL` from the compose file. The two
  tables can stay, or be dropped in `home_database_prod` as postgres with
  `DROP TABLE photofetchr.faces, photofetchr.face_scans; DROP OWNED BY photofetchr_faces; DROP ROLE photofetchr_faces;`.
