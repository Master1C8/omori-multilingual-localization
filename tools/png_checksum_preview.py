#!/usr/bin/env python3
"""Recover a static PNG preview only when the source has an isolated Adler fault.

Never patch the installation, tolerate truncation, or invent missing pixels.
The exact deflate stream is retained; only its Adler and PNG chunk CRC change.
"""
import argparse
import io
import json
from pathlib import Path
import struct
import zlib
from PIL import Image
from research_source import decrypt
from source_media_prepare import decode_rpgmvp
from source_prepare import save_json, sha, strict_json


def preview(original):
    chunks = []
    offset = 8
    if original[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected PNG source')
    while offset < len(original):
        size = struct.unpack('>I', original[offset:offset + 4])[0]
        end = offset + 12 + size
        if end > len(original):
            raise ValueError('Truncated PNG chunk')
        tag, payload = original[offset + 4:offset + 8], original[offset + 8:end - 4]
        crc = struct.unpack('>I', original[end - 4:end])[0]
        if zlib.crc32(tag + payload) & 0xffffffff != crc:
            raise ValueError('Source PNG chunk CRC mismatch')
        chunks.append((tag, payload))
        offset = end
    ihdr = next(v for k, v in chunks if k == b'IHDR')
    width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', ihdr)
    if (depth, color, compression, filtering, interlace) != (8, 6, 0, 0, 0):
        raise ValueError('Preview recovery is bound to non-interlaced 8-bit RGBA only')
    compressed = b''.join(v for k, v in chunks if k == b'IDAT')
    try:
        zlib.decompress(compressed)
    except zlib.error as error:
        if 'incorrect data check' not in str(error):
            raise ValueError('Failure is not isolated to the Adler checksum') from error
    else:
        raise ValueError('Original checksum already valid; no repair needed')
    inflater = zlib.decompressobj(-15)
    pixels = inflater.decompress(compressed[2:-4]) + inflater.flush()
    stride = width * 4 + 1
    if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail or len(pixels) != height * stride:
        raise ValueError('Incomplete or ambiguous pixel stream')
    if any(pixels[y * stride] > 4 for y in range(height)):
        raise ValueError('Invalid PNG filter byte')
    old_adler = compressed[-4:]
    new_adler = struct.pack('>I', zlib.adler32(pixels) & 0xffffffff)
    corrected = compressed[:-4] + new_adler
    if zlib.decompress(corrected) != pixels:
        raise ValueError('Preview changed decompressed pixels')
    parts, inserted = [original[:8]], False
    for tag, payload in chunks:
        if tag == b'IDAT':
            if inserted:
                continue
            payload, inserted = corrected, True
        parts.append(struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff))
    result = b''.join(parts)
    image = Image.open(io.BytesIO(result))
    image.load()
    return result, {'width': width, 'height': height, 'oldAdlerHex': old_adler.hex(), 'newAdlerHex': new_adler.hex(),
                    'decompressedPixelStreamSha256': sha(pixels), 'deflateBytesPreservedExactly': True,
                    'fullPixelLengthAndFilters': 'passed', 'previewDecode': 'passed',
                    'originalRuntimeDecode': 'not-run', 'scope': 'static source preview; no localized texture or installation repair'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--asset', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.game_root.resolve(), args.output.resolve()
    if output.exists() or Path(__file__).resolve().parent.parent not in output.parents:
        raise ValueError('Choose a new canonical-project output path')
    asset = (root / args.asset).resolve()
    if root not in asset.parents:
        raise ValueError('Asset path outside original root')
    source = asset.read_bytes()
    system, _ = decrypt(root / 'data/System.KEL')
    original = decode_rpgmvp(source, bytes.fromhex(strict_json(system)['encryptionKey']))
    result, receipt = preview(original)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)
    receipt.update({'asset': args.asset, 'sourceRawSha256': sha(source), 'decodedSourceRawSha256': sha(original),
                    'previewRawSha256': sha(result), 'recipeRawSha256': sha(Path(__file__).read_bytes()),
                    'originalReadBackUnchanged': asset.read_bytes() == source})
    save_json(output.with_suffix('.receipt.json'), receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
