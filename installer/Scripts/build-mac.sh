#!/bin/zsh
# Adapted from StardewTranslationInstaller Scripts/build-app.sh.
set -euo pipefail
project_dir="${0:A:h:h}"
payload="${1:-$project_dir/../source/release-payload-1.0.0}"
payload="${payload:A}"
if [[ "$payload" == "${project_dir:h}/source/release-payload-1.0.0" && ! -d "$payload" ]]; then
 python3 -B "$project_dir/../scripts/restore_archival_inputs.py" --input release-payload-1.0.0
fi
[[ -f "$payload/payload-receipt.json" ]] || { echo 'Pass a prepared payload folder' >&2; exit 1; }
cd "$project_dir"
release_dir="${OMORI_RELEASE_DIR:-$project_dir/../dist/installer/1.0.0}"
app="$release_dir/OMORI Translation Installer.app"
archive="$release_dir/OMORI-Installer-macOS-1.0.0.zip"
[[ ! -e "$app" && ! -e "$archive" ]] || { echo 'Preserve existing release; select a new revision' >&2; exit 1; }
scratch_root="${OMORI_SWIFT_SCRATCH_PATH:-$project_dir/../build/installer}"
export CLANG_MODULE_CACHE_PATH="$scratch_root/module-cache"
export SWIFT_MODULECACHE_PATH="$CLANG_MODULE_CACHE_PATH"
export SWIFTPM_MODULECACHE_OVERRIDE="$CLANG_MODULE_CACHE_PATH"
arm_binary=""
x86_binary=""
for arch in arm64 x86_64; do
 swift build --build-system native -c release --product OmoriInstaller --disable-sandbox --scratch-path "$scratch_root/swift-$arch" --triple "$arch-apple-macosx14.0"
 bin_dir="$(swift build --build-system native -c release --product OmoriInstaller --disable-sandbox --scratch-path "$scratch_root/swift-$arch" --triple "$arch-apple-macosx14.0" --show-bin-path)"
 if [[ "$arch" == arm64 ]]; then arm_binary="$bin_dir/OmoriInstaller"; else x86_binary="$bin_dir/OmoriInstaller"; fi
done
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
lipo -create "$arm_binary" "$x86_binary" -output "$app/Contents/MacOS/OMORI Translation Installer"
cp "$project_dir/App/Info.plist" "$app/Contents/Info.plist"
cp -R "$payload" "$app/Contents/Resources/Payload"
python3 - "$payload" "$app/Contents/Resources/PackageConfig.json" <<'PY'
import json,sys,pathlib
j=json.loads((pathlib.Path(sys.argv[1])/'payload-receipt.json').read_text());pathlib.Path(sys.argv[2]).write_text(json.dumps({'catalogSha256':j['catalogSha256']}))
PY
python3 Scripts/write_site_locale_manifest.py "$app/Contents/Resources" macos
codesign --force --deep --sign - "$app"
ditto -c -k --norsrc --noextattr --noqtn --keepParent "$app" "$archive"
echo "$app"
