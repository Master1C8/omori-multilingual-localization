#!/usr/bin/env python3
"""Decode every frame of pinned original movies; no game launch or localization."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to(root / 'source') or output.exists():
        raise ValueError('Use a new derivative source directory in the canonical project')
    manifest_path = root / 'source/media-8879120-02/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    game = Path('/Users/antonkrutov/Library/Application Support/Steam/steamapps/common/OMORI/OMORI.app/Contents/Resources/app.nw')
    ffmpeg = root / 'tools/python-deps/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1'
    movies = [r for r in manifest['assets'] if r['asset'].endswith('.webm')]
    for row in movies:
        if sha(game / row['asset']) != row['rawSha256']:
            raise ValueError('Original movie changed: ' + row['asset'])
    output.mkdir()
    results = []
    save(output / 'INCOMPLETE.json', {'status': 'incomplete', 'sourceManifestSha256': sha(manifest_path),
          'recipeSha256': sha(Path(__file__)), 'ffmpegSha256': sha(ffmpeg),
          'recovery': 'Per-movie receipts are reusable after checking their full hashes. Preserve unfinished folders; do not label them complete.'})
    for index, row in enumerate(movies):
        if shutil.disk_usage(root).free < 4 * 1024 ** 3:
            raise ValueError('Insufficient free space for uncapped source frame extraction; preserve partial output')
        directory = output / f'movie-{index:02d}'
        directory.mkdir()
        frames = directory / 'frames'; frames.mkdir()
        command = [str(ffmpeg), '-hide_banner', '-nostdin', '-v', 'error', '-i', str(game / row['asset']),
                   '-map', '0:v:0', '-fps_mode', 'passthrough', '-compression_level', '3',
                   str(frames / 'frame-%06d.png'), '-map', '0:v:0', '-f', 'framemd5', str(directory / 'frames.framemd5')]
        with (directory / 'decoder.log').open('x') as log:
            run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if run.returncode:
            raise ValueError('Movie decoding failed: ' + row['asset'])
        native_hashes = (directory / 'frames.framemd5').read_text().splitlines()
        records = [line for line in native_hashes if line and not line.startswith('#')]
        files = sorted(frames.glob('frame-*.png'))
        if not records or len(files) != len(records):
            raise ValueError('Movie frame/output count mismatch')
        hashes = [{'frame': n + 1, 'path': str(path.relative_to(output)), 'sha256': sha(path),
                   'decodedFrameRecord': records[n]} for n, path in enumerate(files)]
        save(directory / 'frame-index.json', hashes)
        result = {'asset': row['asset'], 'sourceSha256': row['rawSha256'], 'status': 'decoded-all-frames',
                  'frames': len(files), 'exactUniquePngFrames': len({r['sha256'] for r in hashes}),
                  'frameIndex': {'path': str((directory / 'frame-index.json').relative_to(output)),
                                 'sha256': sha(directory / 'frame-index.json')},
                  'decoderFrameHashes': {'path': str((directory / 'frames.framemd5').relative_to(output)),
                                        'sha256': sha(directory / 'frames.framemd5')},
                  'command': command, 'inputSha256After': sha(game / row['asset']),
                  'visualTextClassification': 'pending', 'runtime': 'not-run'}
        if result['inputSha256After'] != row['rawSha256']:
            raise ValueError('Movie changed during extraction')
        save(directory / 'receipt.json', result)
        results.append(result)
        print(json.dumps({'asset': row['asset'], 'decodedFrames': len(files),
                          'exactUniqueFrames': result['exactUniquePngFrames']}), flush=True)
    save(output / 'manifest.json', {'status': 'all-pinned-movies-decoded', 'sourceManifest': {
        'path': str(manifest_path.relative_to(root)), 'sha256': sha(manifest_path)},
        'recipeSha256': sha(Path(__file__)), 'ffmpegSha256': sha(ffmpeg), 'movies': results,
        'frames': sum(r['frames'] for r in results), 'caps': 'none; every decoded video frame retained at native cadence',
        'scope': 'Source extraction only. No lexical/visual acceptance, translated movie, game launch or installed/save change.'})


if __name__ == '__main__':
    main()
