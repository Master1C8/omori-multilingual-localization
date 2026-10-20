#!/usr/bin/env python3
"""Build a local Windows release and record verifiable, unsigned provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import zipfile


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def inventory(root):
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink input is not permitted: " + str(path))
        if path.is_file():
            rows.append({"path": path.relative_to(root).as_posix(),
                         "sizeBytes": path.stat().st_size, "sha256": digest(path)})
    if not rows:
        raise ValueError("Empty material inventory")
    return rows


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def verify_archive(archive, stage, manifest=None):
    expected = {f"{stage.name}/{row['path']}": row for row in inventory(stage)}
    if manifest is not None:
        expected[manifest.name] = {"sizeBytes": manifest.stat().st_size, "sha256": digest(manifest)}
    with zipfile.ZipFile(archive) as package:
        entries = [item for item in package.infolist() if not item.is_dir()]
        if len(entries) != len({item.filename for item in entries}):
            raise ValueError("Duplicate archive entries")
        if {item.filename for item in entries} != set(expected):
            raise ValueError("Archive/stage paths differ")
        for item in entries:
            value = hashlib.sha256()
            with package.open(item) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    value.update(block)
            row = expected[item.filename]
            if item.file_size != row["sizeBytes"] or value.hexdigest() != row["sha256"]:
                raise ValueError("Archive/stage bytes differ: " + item.filename)
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--release", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    payload, release = args.payload.resolve(), args.release.resolve()
    if not release.is_relative_to(root / "dist"):
        raise ValueError("Release must be inside this project's dist directory")
    if release.exists():
        raise ValueError("Existing release preserved; choose a new path")
    if git(root, "branch", "--show-current") != "main":
        raise ValueError("Build from canonical main")
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("Commit source changes before building")
    repository = "https://github.com/Master1C8/omori-multilingual-localization"
    if git(root, "remote", "get-url", "origin").removesuffix(".git") != repository:
        raise ValueError("Unexpected source repository")
    commit, tree = git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")
    if git(root, "rev-parse", "origin/main") != commit:
        raise ValueError("Push canonical main before preparing provenance")
    receipt = json.loads((payload / "payload-receipt.json").read_text())
    if receipt.get("pendingLocales") != [] or len(receipt.get("locales", [])) != 27:
        raise ValueError("Expected the complete retained payload")
    if digest(payload / "catalog.json") != receipt["catalogSha256"]:
        raise ValueError("Payload catalog does not match its receipt")
    materials = inventory(payload)
    tools = {}
    for name in ["x86_64-w64-mingw32-gcc", "x86_64-w64-mingw32-g++",
                 "x86_64-w64-mingw32-windres", "x86_64-w64-mingw32-ar",
                 "x86_64-w64-mingw32-ranlib", "make", "zip", "zsh", "python3"]:
        path = shutil.which(name)
        if not path:
            raise ValueError("Required tool missing: " + name)
        tools[name] = {"path": str(Path(path).resolve()), "sha256": digest(path)}
    started = datetime.now(timezone.utc).isoformat()
    release.mkdir(parents=True)
    command = ["zsh", "installer/Scripts/build-windows.sh", str(payload)]
    with (release / "build.log").open("w") as log:
        subprocess.run(command, cwd=root, env={**os.environ, "OMORI_RELEASE_DIR": str(release)},
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    if git(root, "rev-parse", "HEAD") != commit or git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("Source changed during build; provenance not accepted")
    if inventory(payload) != materials:
        raise ValueError("Payload changed during build; provenance not accepted")
    archive = release / "OMORI-Installer-Windows-1.0.0.zip"
    stage = release / "OMORI Installer Windows"
    embedded = release / "vnrevival-release.json"
    embedded.write_text(json.dumps({
        "schemaVersion": 1, "gameSlug": "omori", "platform": "windows", "version": "1.0.0",
        "sourceTreeClean": True, "sourceCommit": commit, "repositoryUrl": repository,
        "sourceTree": tree, "payloadInventorySha256": fingerprint(materials),
        "recipe": "installer/Scripts/build-provenance.py",
    }, indent=2) + "\n")
    with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED) as package:
        package.write(embedded, embedded.name)
    entries = verify_archive(archive, stage, embedded)
    executables = []
    for exe in [stage / "OMORI Translation Installer.exe", stage / "Resources/OmoriInstallHelper.exe"]:
        with exe.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise ValueError("Missing PE executable")
            stream.seek(0x3c)
            offset = int.from_bytes(stream.read(4), "little")
            stream.seek(offset)
            if stream.read(6) != b"PE\0\0\x64\x86":
                raise ValueError("Expected Windows x86-64 executable")
        executables.append({"path": exe.relative_to(stage).as_posix(), "sha256": digest(exe)})
    record = {
        "schemaVersion": 1, "version": "1.0.0", "publication": "not-published",
        "source": {"repository": repository, "commit": commit, "tree": tree,
                   "url": f"{repository}/tree/{commit}"},
        "build": {"recipe": "installer/Scripts/build-provenance.py", "platform": "windows",
                  "architecture": "x86_64", "startedAt": started,
                  "completedAt": datetime.now(timezone.utc).isoformat(),
                  "method": "local cross-compilation on macOS", "tools": tools,
                  "logSha256": digest(release / "build.log")},
        "materials": {"payloadInventory": "payload-materials.json",
                      "inventorySha256": fingerprint(materials),
                      "catalogSha256": receipt["catalogSha256"],
                      "locales": receipt["locales"],
                      "availability": "Retained local payload; not distributed by the public source repository."},
        "artifact": {"filename": archive.name, "sizeBytes": archive.stat().st_size,
                     "sha256": digest(archive), "verifiedEntries": entries,
                     "executables": executables},
        "assurance": {"statement": "unsigned local build record",
                      "publisherSignature": None, "buildAttestation": None,
                      "notarization": "not applicable to Windows",
                      "independentSecurityReview": None,
                      "runtimeTesting": "not performed by this build recipe"},
    }
    (release / "payload-materials.json").write_text(json.dumps(materials, indent=2) + "\n")
    # Completion is the last marker. Failures preserve diagnostics without this marker.
    temporary = release / "provenance.json.tmp"
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    (release / "SHA256SUMS").write_text(f"{record['artifact']['sha256']}  {archive.name}\n")
    temporary.replace(release / "provenance.json")
    print(json.dumps({"archive": str(archive), "sha256": record["artifact"]["sha256"],
                      "sourceCommit": commit, "verifiedEntries": entries}))


if __name__ == "__main__":
    main()
