import time
import msgpack

class Codec:
    def __init__(self):
        self._seq = 0

    def pack(self, payload: dict) -> bytes:
        payload = dict(payload or {})
        payload.setdefault("ts", time.time())
        payload.setdefault("seq", self._seq)
        self._seq += 1
        return msgpack.packb(payload, use_bin_type=True)

    @staticmethod
    def unpack(raw: bytes) -> dict:
        return msgpack.unpackb(raw, raw=False)