#!/usr/bin/env python3
"""Read original images into static review material. No localization or installation."""
import argparse
import io
import json
from pathlib import Path
import sys
from PIL import Image
from research_source import decrypt
from source_prepare import save_json, sha, strict_json


def decode_rpgmvp(raw, key):
    expected = bytes.fromhex('5250474d560000000003010000000000')
    if raw[:16] != expected or len(raw) < 32:
        raise ValueError('RPGMV image header mismatch')
    body = bytearray(raw[16:])
    for i in range(16):
        body[i] ^= key[i]
    # RPGMV's decrypter does not enforce PNG content. This installation also
    # encrypts JPEGs with the .rpgmvp extension. Sniff bytes before naming output.
    if body[:8] != b'\x89PNG\r\n\x1a\n' and body[:3] != b'\xff\xd8\xff':
        raise ValueError('Decoded image signature is neither PNG nor JPEG')
    return bytes(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.game_root.resolve(), args.output.resolve()
    project = Path(__file__).resolve().parent.parent
    if out.exists() or project not in out.parents or root in out.parents:
        raise ValueError('Choose a new output directory in the canonical project')
    data, system_hash = decrypt(root / 'data/System.KEL')
    key = bytes.fromhex(strict_json(data)['encryptionKey'])
    out.mkdir(parents=True)
    rows = []
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in {'.rpgmvp', '.png', '.jpg', '.webm'}:
            continue
        asset = p.relative_to(root).as_posix()
        raw = p.read_bytes()
        row = {'asset': asset, 'rawSha256': sha(raw), 'sourceTextStatus': 'needs-full-visual-review',
               'localization': 'not-started', 'runtime': 'not-run'}
        if p.suffix == '.webm':
            row['decodeStatus'] = 'not-run'
            row['reason'] = 'Movie text/credits require separately decoded static frames; no video decoder bound yet.'
        else:
            try:
                decoded = decode_rpgmvp(raw, key) if p.suffix == '.rpgmvp' else raw
                image = Image.open(io.BytesIO(decoded))
                image.load()
                row.update({'size': list(image.size), 'mode': image.mode, 'format': image.format,
                            'decodedRawSha256': sha(decoded), 'decodeStatus': 'passed'})
                suffix = '.jpg' if image.format == 'JPEG' else '.png'
                target = out / 'decoded' / Path(asset).with_suffix(suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(decoded)
                row['output'] = str(target.relative_to(out))
            except Exception as error:
                row['decodeStatus'] = 'failed'
                row['reason'] = str(error)
        rows.append(row)
    save_json(out / 'manifest.json', {'schemaVersion': 1, 'steamBuild': '8879120', 'systemEncryptedRawSha256': system_hash,
                                    'decoderRecipeRawSha256': sha(Path(__file__).read_bytes()), 'assets': rows,
                                    'imageDecodePassed': sum(r['decodeStatus'] == 'passed' for r in rows),
                                    'imageDecodeFailed': sum(r['decodeStatus'] == 'failed' for r in rows),
                                    'moviesNotRun': sum(r['asset'].endswith('.webm') for r in rows),
                                    'visualReview': 'not-run', 'imageTextInventory': 'pending',
                                    'limits': ['Decoded source images are static extraction, not localized textures.',
                                               'Neither a successful decode nor empty OCR proves absence of visible text.']})
    print(json.dumps({'resources': len(rows), 'decoded': sum(r['decodeStatus'] == 'passed' for r in rows),
                      'failed': [r for r in rows if r['decodeStatus'] == 'failed'],
                      'movieText': 'pending', 'visualReview': 'not-run'}, indent=2))


if __name__ == '__main__':
    main()
