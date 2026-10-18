#!/usr/bin/env python3
"""Read original OMORI assets into a reproducible glossary-research index.

This is research extraction, not a translation/reinsertion adapter. Unknown
runtime roles stay pending; technical strings are never counted as visible text.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import yaml


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decrypt(path):
    data = path.read_bytes()
    if len(data) < 16:
        raise ValueError(f"Truncated encrypted file: {path}")
    decoder = Cipher(algorithms.AES(b"6bdb2e585882fbd48826ef9cffd4c511"),
                     modes.CTR(data[:16])).decryptor()
    return (decoder.update(data[16:]) + decoder.finalize()).decode("utf-8"), digest(data)


def scalars(value, path=(), ancestors=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from scalars(child, path + (key,), ancestors + (value,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from scalars(child, path + (index,), ancestors + (value,))
    else:
        yield path, value, ancestors


def role(file, path, value, ancestors):
    if not isinstance(value, str):
        return "preserve-exactly"
    key = path[-1] if path else None
    if file.suffix == ".HERO":
        if key in ("faceset", "source", "tag", "replace") or any(
            key in path for key in ("background", "character", "inputKeysTable", "InputIcons", "InputNames")
        ):
            return "preserve-exactly"
        if re.fullmatch(r"[\w-]+\.message_\w+", value):
            return "preserve-exactly"
        if key in ("text", "help"):
            return "visible-candidate"
        if file.name == "Bestiary.HERO" and key == "name":
            return "visible-candidate"
        if file.name in ("XX_BLUE.HERO", "System.HERO", "Database.HERO"):
            return "needs-role-review"
        return "needs-role-review"
    if file.name == "Quests.PLUTO":
        return "preserve-exactly" if re.fullmatch(r"[\w-]+\.message_\w+", value) else "needs-role-review"
    if file.suffix == ".PLUTO":
        return "preserve-exactly"
    database_fields = {
        "Actors": {"name", "nickname", "profile"}, "Armors": {"name", "description"},
        "Items": {"name", "description"}, "Weapons": {"name", "description"},
        "Classes": {"name"}, "Enemies": {"name"},
        "Skills": {"name", "description", "message1", "message2"},
        "States": {"name", "message1", "message2", "message3", "message4"},
    }
    if key in database_fields.get(file.stem, set()):
        return "visible-candidate"
    if key == "displayName" or (file.stem == "System" and any(
        k in path for k in ("terms", "currencyUnit", "gameTitle", "armorTypes", "equipTypes", "skillTypes", "weaponTypes")
    )):
        return "visible-candidate"
    if "parameters" in path:
        command = next((a for a in reversed(ancestors) if isinstance(a, dict) and "code" in a), None)
        if command:
            tail = path[path.index("parameters") + 1:]
            if command["code"] in (401, 405) and tail == (0,):
                return "visible-candidate"
            if command["code"] == 102 and len(tail) == 2 and tail[0] == 0:
                return "visible-candidate"
            if command["code"] == 402 and tail == (1,):
                return "visible-candidate"
            return "preserve-exactly"
    if key == "note":
        return "needs-role-review"
    return "preserve-exactly"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root, out = args.game_root.resolve(), args.output.resolve()
    if out == root or root in out.parents or out in root.parents:
        raise ValueError("Research output must be separate from the installation")
    if not (root / "languages/en").is_dir() or not (root / "data").is_dir():
        raise ValueError("Expected English original asset root")
    if out.exists():
        raise ValueError("Preserve immutable research output; choose a new output directory")

    plugins_raw = (root / "js/plugins.js").read_bytes()
    plugin_text = plugins_raw.decode("utf-8")
    plugins = json.JSONDecoder().raw_decode(plugin_text[plugin_text.index("["):])[0]
    actors, _ = decrypt(root / "data/Actors.KEL")
    actor_names = {str(a["id"]): a["name"] for a in json.loads(actors) if a}
    macros = {}
    macro_definitions = []
    for plugin in plugins:
        if plugin["status"] and plugin["name"].startswith("YEP_X_MessageMacros"):
            for key, name in plugin["parameters"].items():
                match = re.fullmatch(r"Macro (\d+) Name", key)
                if match and name and name != "undefined":
                    text = plugin["parameters"][f"Macro {match[1]} Text"]
                    if "\\n<" in text:
                        macro_definitions.append({"id": int(match[1]), "name": name, "text": text,
                                                  "plugin": plugin["name"]})
    macro_definitions.sort(key=lambda row: row["id"])
    for row in macro_definitions:
        # The actual quick-macro renderer replaces in numeric ID order. A later
        # duplicate name cannot replace a token already consumed by an earlier ID.
        macros.setdefault(row["name"].lower(), row["text"])

    files = sorted((root / "languages/en").glob("*.HERO")) + sorted((root / "data").glob("*.KEL")) + sorted((root / "data").glob("*.PLUTO"))
    manifest, records, roster = [], [], defaultdict(list)
    seen = set()
    for file in files:
        text, file_hash = decrypt(file)
        from source_prepare import strict_yaml
        data = json.loads(text) if file.suffix == ".KEL" else strict_yaml(text)
        roundtrip = json.loads(json.dumps(data, ensure_ascii=False)) if file.suffix == ".KEL" else strict_yaml(yaml.safe_dump(data, allow_unicode=True))
        if data != roundtrip:
            raise ValueError(f"Parsed-value no-op roundtrip failed: {file}")
        rel = file.relative_to(root).as_posix()
        manifest.append({"asset": rel, "encryptedSha256": file_hash, "parsedRoundtrip": "passed"})
        for path, value, ancestors in scalars(data):
            if not isinstance(value, str):
                continue
            # Typed YAML keys distinguish integer 0 from string "0".
            identity = rel + "#" + json.dumps(path, ensure_ascii=False, separators=(",", ":"))
            if identity in seen:
                raise ValueError(f"Duplicate scalar identity: {identity}")
            seen.add(identity)
            record = {"id": identity, "asset": rel, "path": path, "source": value,
                      "role": role(file, path, value, ancestors)}
            records.append(record)
    text_records = [row for row in records if row["path"] and row["path"][-1] == "text"]
    helper = Path(__file__).with_name("expand_speaker_macros.mjs")
    result = subprocess.run(["node", str(helper), str(root)],
                            input=json.dumps([row["source"] for row in text_records]),
                            text=True, capture_output=True, check=True)
    dispatched = json.loads(result.stdout)
    if len(dispatched["expanded"]) != len(text_records):
        raise ValueError("Macro-dispatch alignment differs")
    for row, expanded in zip(text_records, dispatched["expanded"]):
        # The macro plugin uses ESC internally. Actor substitution here is a
        # static binding to original Actors.KEL, not a simulation of player renaming.
        expanded = expanded.replace("\x1b", "\\")
        expanded = re.sub(r"\\n\[(\d+)\]", lambda m: actor_names.get(m[1], m[0]), expanded, flags=re.I)
        labels = re.findall(r"\\n(?:[1-5c])?<([^>]+)>", expanded, re.I)
        labels += re.findall(r"\\>([^:\\]+):\s*\\<", expanded)
        for label in labels:
            roster[label].append(row["id"])

    output = {
        "schemaVersion": 1, "sourceLocale": "en", "steamBuild": "8879120",
        "gameRoot": str(root), "pluginConfigurationSha256": digest(plugins_raw),
        "assets": manifest, "researchOnly": True,
        "macroDispatchPluginHashes": dispatched["pluginHashes"],
        "limitations": ["Visible candidates are not an approved translation inventory.",
                        "Speaker labels may denote dates, groups or objects; identity review remains required.",
                        "Plugin literals, parameter-derived text and image text are not fully inventoried.",
                        "Parsed-value roundtrip does not prove packaging or runtime reinsertion."],
    }
    out.mkdir(parents=True)
    index = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records)
    (out / "strings.jsonl").write_text(index, encoding="utf-8")
    output["researchIndexSha256"] = digest(index.encode())
    output["counts"] = dict(Counter(r["role"] for r in records))
    output["assetCount"] = len(manifest)
    output["speakerLabelCount"] = len(roster)
    (out / "manifest.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    roster_rows = [{"label": label, "occurrences": len(ids), "sourceIds": ids, "status": "needs-identity-review"} for label, ids in sorted(roster.items())]
    (out / "speaker-labels.json").write_text(json.dumps(roster_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "speaker-macros.json").write_text(json.dumps(macro_definitions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("assetCount", "counts", "speakerLabelCount", "researchIndexSha256")}, indent=2))


if __name__ == "__main__":
    main()
