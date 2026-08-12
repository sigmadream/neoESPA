import zlib
import base64

def compress_text(text: str) -> str:
    """Compress text using zlib and encode to base64 for DB storage."""
    if not text:
        return ""
    compressed = zlib.compress(text.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')

def decompress_text(compressed_base64: str) -> str:
    """Decompress base64-encoded zlib data back to original text."""
    if not compressed_base64:
        return ""
    try:
        compressed_bytes = base64.b64decode(compressed_base64)
        decompressed = zlib.decompress(compressed_bytes)
        return decompressed.decode('utf-8')
    except (zlib.error, ValueError, base64.binascii.Error):
        # Fallback for uncompressed legacy data
        return compressed_base64
