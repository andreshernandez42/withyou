#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/mobile"
TMP="$(mktemp -d)"
cp -r lib "$TMP/lib"
cp pubspec.yaml "$TMP/pubspec.yaml"
cp analysis_options.yaml "$TMP/analysis_options.yaml"
flutter create . --platforms=android,ios --project-name with_you
rm -rf lib
cp -r "$TMP/lib" lib
cp "$TMP/pubspec.yaml" pubspec.yaml
cp "$TMP/analysis_options.yaml" analysis_options.yaml
flutter pub get
python "$ROOT/scripts/patch_mobile.py"
echo "Mobile bootstrap completado."
