#!/usr/bin/env python3
"""Initialize only absent native macOS cutscene metadata; preserve existing data."""
import json
from pathlib import Path
folder=Path('/Users/antonkrutov/Library/Preferences/com.omocat.omori');file=folder/'CUTSCENE.json'
if file.exists():
    assert file.is_file() and not file.is_symlink(), 'Unexpected existing cutscene metadata'
    print('Existing metadata preserved; no write.')
else:
    folder.mkdir(exist_ok=True)
    with file.open('x') as stream:stream.write('{}')
    assert json.loads(file.read_text())=={}
    print('Initialized absent native cutscene metadata with the native empty default.')
