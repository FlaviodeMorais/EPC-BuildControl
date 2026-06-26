"""Leitor binário de arquivos Paradox .DB (engenharia reversa)."""

import struct


def parse(path: str) -> tuple[list[str], list[dict]]:
    with open(path, 'rb') as f:
        raw = f.read()

    rec_size = struct.unpack_from('<H', raw, 0)[0]
    hdr_size = struct.unpack_from('<H', raw, 2)[0]
    n_fields = struct.unpack_from('<H', raw, 33)[0]

    fields = [(raw[120 + i * 2], raw[121 + i * 2]) for i in range(n_fields)]

    # Nomes: strings ASCII null-terminated após offset 400
    names: list[str] = []
    pos = 400
    while pos < hdr_size - 1 and len(names) < n_fields:
        if 32 <= raw[pos] < 127:
            end = pos
            while end < hdr_size and raw[end] != 0:
                end += 1
            name = raw[pos:end].decode('latin-1', 'replace')
            if len(name) >= 2 and all(32 <= ord(c) < 127 for c in name):
                names.append(name)
                pos = end + 1
            else:
                pos += 1
        else:
            pos += 1
    names += [f'f{i}' for i in range(len(names), n_fields)]

    def _decode(data: bytes, ftype: int):
        if not any(data):
            return None
        if ftype in (1, 14, 15):
            s = data.rstrip(b'\x00').decode('latin-1', 'replace')
            return (''.join(c for c in s if ord(c) >= 32)).strip() or None
        if ftype in (4, 22):
            v = struct.unpack('>I', data)[0] ^ 0x80000000
            return v or None
        if ftype == 3:
            v = struct.unpack('>H', data)[0] ^ 0x8000
            return v or None
        if ftype == 6:
            b = bytearray(data)
            if b[0] & 0x80:
                b[0] &= 0x7F
            else:
                for i in range(len(b)):
                    b[i] ^= 0xFF
            try:
                v = struct.unpack('>d', bytes(b))[0]
                return round(v, 4) if v and abs(v) < 1e15 else None
            except Exception:
                return None
        if ftype == 2:
            v = struct.unpack('>I', data)[0] ^ 0x80000000
            if 1 < v < 3_000_000:
                from datetime import date, timedelta
                try:
                    return date(1, 1, 1) + timedelta(days=v - 1)
                except Exception:
                    pass
            return None
        if ftype == 9:
            return bool(data[0] & 0x80)
        return data.rstrip(b'\x00').decode('latin-1', 'replace').strip() or None

    # Detecta block_leader verificando se campo 1 começa com prefixo conhecido
    iso_off = fields[0][1]
    iso_sz = fields[1][1]
    prefixes = (b'4710', b'4730', b'6100', b'B065', b'01', b'02', b'03')
    block_size = hdr_size
    best = 4
    for leader in (4, 6, 8, 10):
        blk = raw[hdr_size:hdr_size + block_size]
        chunk = blk[leader + iso_off: leader + iso_off + iso_sz]
        if any(chunk.startswith(p) for p in prefixes):
            best = leader
            break

    records: list[dict] = []
    off = hdr_size
    while off + block_size <= len(raw):
        blk = raw[off:off + block_size]
        rp = best
        while rp + rec_size <= block_size:
            rec = blk[rp:rp + rec_size]
            if any(rec):
                row: dict = {}
                fp = 0
                for name, (ft, fs) in zip(names, fields):
                    row[name] = _decode(rec[fp:fp + fs], ft)
                    fp += fs
                if any(v for v in row.values() if v is not None):
                    records.append(row)
            rp += rec_size
        off += block_size

    return names, records
