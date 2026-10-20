#!/bin/zsh
# Adapted from the proven VN Revival native Windows build script.
set -euo pipefail
project_dir="${0:A:h:h}"
payload="${1:A}"
[[ -f "$payload/payload-receipt.json" ]] || { echo 'Pass a completed payload folder' >&2; exit 1; }
cd "$project_dir"
compiler=/opt/homebrew/bin/x86_64-w64-mingw32-gcc
cpp=/opt/homebrew/bin/x86_64-w64-mingw32-g++
windres=/opt/homebrew/bin/x86_64-w64-mingw32-windres
release_dir="${OMORI_RELEASE_DIR:-$project_dir/../dist/installer/1.0.0}"
stage="$release_dir/OMORI Installer Windows"
[[ ! -e "$stage" && ! -e "$release_dir/OMORI-Installer-Windows-1.0.0.zip" ]] || { echo 'Preserve existing release; select a new revision' >&2; exit 1; }
mkdir -p "$stage/Resources" "$project_dir/../build/installer"
make -B -C vendor/zlib-1.3.1 CC="$compiler" AR=/opt/homebrew/bin/x86_64-w64-mingw32-ar RANLIB=/opt/homebrew/bin/x86_64-w64-mingw32-ranlib libz.a
"$windres" Windows/Installer.rc -O coff -o ../build/installer/windows-resources.o
# Both executables need asInvoker: CreateProcess cannot satisfy installer-detection elevation.
"$cpp" -std=c++17 -O2 -s -Wall -Wextra -Wno-misleading-indentation -municode -static -static-libgcc -static-libstdc++ Windows/OmoriInstallHelper.cpp ../build/installer/windows-resources.o -Ivendor/zlib-1.3.1 vendor/zlib-1.3.1/libz.a -o "$stage/Resources/OmoriInstallHelper.exe" -lbcrypt -ladvapi32
"$compiler" -std=c11 -O2 -s -Wall -Wextra -Werror -municode -mwindows Windows/OmoriTranslationInstaller.c ../build/installer/windows-resources.o -o "$stage/OMORI Translation Installer.exe" -lcomctl32 -lshell32 -lole32 -luuid
cp -R "$payload" "$stage/Resources/Payload"
python3 - "$payload" "$stage/Resources" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);j=json.loads((p/'payload-receipt.json').read_text());(out/'PackageConfig.json').write_text(json.dumps({'catalogSha256':j['catalogSha256']}));c=json.loads((p/'catalog.json').read_text());(out/'languages.tsv').write_text(''.join(l['code']+'\t'+l['name']+'\n' for l in c['locales']))
PY
python3 Scripts/write_site_locale_manifest.py "$stage/Resources" windows
cp Windows/README.txt "$stage/README.txt"
cd "$release_dir"
/usr/bin/zip -q -r -X OMORI-Installer-Windows-1.0.0.zip 'OMORI Installer Windows'
/usr/bin/unzip -tq OMORI-Installer-Windows-1.0.0.zip >/dev/null
echo "$stage"
