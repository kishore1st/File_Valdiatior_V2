import hashlib

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

async def sha256_stream(chunks) -> str:
    h = hashlib.sha256()
    async for chunk in chunks:
        h.update(chunk)
    return h.hexdigest()