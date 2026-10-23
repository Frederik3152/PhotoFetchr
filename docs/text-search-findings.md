# Text search: findings from the prototype (postponed)

Searching photos by describing them ("snow", "a birthday cake") by comparing a text
embedding with an image embedding per photo. Tested on 2026-10-22 on 212 photos, then put
on hold to focus on face suggestions. The code and the `photofetchr.picture_embeddings`
table were removed; this note is what's left.

## What was tested

Two models, both run through [fastembed](https://github.com/qdrant/fastembed) on
onnxruntime (no PyTorch), CPU only, on the dev container:

| Model | Dimensions | Languages | Image embedding | Peak memory, image model | Text model |
| --- | --- | --- | --- | --- | --- |
| CLIP ViT-B/32 (`Qdrant/clip-ViT-B-32-*`) | 512 | English | 0.06 s/photo | ~800 MB | small, fits easily |
| SigLIP2 base (`google/siglip2-base-patch16-224`) | 768 | multilingual | 0.14 s/photo | ~800 MB | 1.13 GB on disk, killed at an 1.8 GB cap |

Fetching and decoding each original took 0.25–0.5 s, more than either model, so a full
run over the 6,613 photos is mostly I/O: roughly 45–60 minutes.

## What we learned

- **CLIP ViT-B/32 does not understand Danish.** English and Danish versions of the same
  query returned mostly different photos: "snow"/"sne" shared 0 of the top 6,
  "a beach"/"strand" 1, "a christmas tree"/"juletræ" 2.
- **Danish search needs a multilingual model, and that costs memory where the searches
  run.** The query has to be embedded at search time, so the text model stays loaded in
  whatever serves the search. SigLIP2's text model needed more than 1.8 GB, which neither
  the dev container (3 GB) nor app-deployment-vm (about 1.5 GB free) has to spare. The
  `local-llm` container (10.7 GB, mostly unused) could host it.
- **Search quality was never judged.** The contact sheet of CLIP results was built but not
  reviewed, and SigLIP2's results were never produced.
- **One model per process.** Each model holds several hundred MB; loading three at once
  ran the dev container out of memory and crashed it.

## Picking it up again

1. Decide whether search must work in Danish. If English is enough, CLIP ViT-B/32 is
   small and could run next to PhotoFetchr.
2. If Danish matters, compare SigLIP2 (and jina-clip-v1, also in fastembed) somewhere
   with 3+ GB free, and decide where the text model lives in production.
3. pgvector is already in the shared `extensions` schema; the column can be `vector(n)`
   with an HNSW index once the model is chosen.
