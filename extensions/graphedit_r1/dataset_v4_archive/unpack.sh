#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$SCRIPT_DIR/.."
B64="$SCRIPT_DIR/final_event_v4_update.tar.gz.b64"
ARCHIVE="$SCRIPT_DIR/final_event_v4_update.tar.gz"
EXPECTED_SHA256="b6b2ee990d8a3720cb86b6e2296fa356894a51613a192717d773748d5c05a2e1"

base64 --decode "$B64" > "$ARCHIVE"
ACTUAL_SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
if [[ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]]; then
  echo "ERROR: SHA-256 mismatch" >&2
  echo "expected: $EXPECTED_SHA256" >&2
  echo "actual:   $ACTUAL_SHA256" >&2
  rm -f "$ARCHIVE"
  exit 1
fi

rm -rf "$TARGET_DIR/dataset_v4"
tar -xzf "$ARCHIVE" -C "$TARGET_DIR"
rm -f "$ARCHIVE"

echo "Extracted current data adapter to:"
echo "  $TARGET_DIR/dataset_v4"
echo
echo "Next:"
echo "  read $TARGET_DIR/dataset_v4/README.md"
