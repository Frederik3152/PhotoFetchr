from PIL import Image

# EXIF orientation -> the transpose that turns the image upright. Pillow's
# ImageOps.exif_transpose does the same but also rewrites the EXIF block, which fails on
# photos with out-of-range values in it; only the rotation is needed here.
ORIENTATION = {2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180,
               4: Image.Transpose.FLIP_TOP_BOTTOM, 5: Image.Transpose.TRANSPOSE,
               6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE,
               8: Image.Transpose.ROTATE_90}

def upright(image):
    """
    The image turned the way its EXIF orientation says
    """
    try:
        method = ORIENTATION.get(image.getexif().get(0x0112, 1))
    except Exception:
        method = None
    # FLIP_LEFT_RIGHT is 0, so compare with None rather than testing truthiness
    return image.transpose(method) if method is not None else image
