import asyncssh
from datetime import datetime
from .base import DiscoveredItem

class SftpConnector:
    def __init__(self, cfg: dict):
        self.host = cfg["host"]
        self.port = cfg.get("port", 22)
        self.username = cfg["username"]
        self.password = cfg.get("password")
        self.key = cfg.get("key")
        self.cursor = None

    async def _connect(self):
        return await asyncssh.connect(
            self.host, port=self.port, username=self.username,
            password=self.password, known_hosts=None,
        )

    async def list_since(self, location, since, cursor):
        path = location["location_key"]
        async with await self._connect() as conn:
            async with conn.start_sftp_client() as sftp:
                async for entry in sftp.scandir(path):
                    if entry.filename.startswith("."):
                        continue
                    attrs = await sftp.stat(f"{path}/{entry.filename}")
                    mtime = datetime.utcfromtimestamp(attrs.mtime)
                    if since and mtime <= since:
                        continue
                    yield DiscoveredItem(
                        ref=f"{path}/{entry.filename}",
                        version=f"{int(attrs.mtime)}:{attrs.size}",
                        name=entry.filename,
                        size=attrs.size,
                        modified_at=mtime,
                        raw={"path": path, "name": entry.filename, "mtime": attrs.mtime},
                    )

    async def fetch(self, item) -> bytes:
        async with await self._connect() as conn:
            async with conn.start_sftp_client() as sftp:
                async with sftp.open(item.ref, "rb") as fh:
                    return await fh.read()