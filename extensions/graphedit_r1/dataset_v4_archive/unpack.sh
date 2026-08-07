#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$SCRIPT_DIR/.."
ENCODED="$SCRIPT_DIR/final_event_v4_update.tar.gz.b64"
ARCHIVE="$SCRIPT_DIR/final_event_v4_update.tar.gz"
EXPECTED_SHA256="ba6e869ade73b253cbdecaed37c19641852a249ffc8ede0e70e9bd020646889b"

if [[ ! -f "$ENCODED" ]]; then
  echo "ERROR: missing encoded adapter archive: $ENCODED" >&2
  exit 1
fi

python3 - "$ENCODED" "$ARCHIVE" "$EXPECTED_SHA256" <<'PY'
from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

encoded_path = Path(sys.argv[1])
archive_path = Path(sys.argv[2])
expected = sys.argv[3].strip().lower()
raw = encoded_path.read_bytes()
alphabet = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
whitespace = set(b" \t\r\n\v\f")
bad = [value for value in raw if value not in alphabet and value not in whitespace]
clean = bytes(value for value in raw if value in alphabet)

print(
    f"[dataset_v4] raw={len(raw)} clean={len(clean)} "
    f"mod4={len(clean) % 4} non_base64={len(bad)}"
)
if bad:
    print(
        f"[dataset_v4][WARN] filtered byte values: {sorted(set(bad))[:20]}",
        file=sys.stderr,
    )

try:
    decoded = base64.b64decode(clean, validate=True)
except Exception as exc:
    print(f"ERROR: Python Base64 decoding failed: {exc}", file=sys.stderr)
    print("This indicates the committed adapter Base64 stream itself is malformed.", file=sys.stderr)
    raise SystemExit(2)

actual = hashlib.sha256(decoded).hexdigest()
print(f"[dataset_v4] decoded_bytes={len(decoded)}")
print(f"[dataset_v4] sha256={actual}")
if actual != expected:
    print("ERROR: SHA-256 mismatch", file=sys.stderr)
    print(f"expected: {expected}", file=sys.stderr)
    print(f"actual:   {actual}", file=sys.stderr)
    print("The committed adapter archive is corrupted; do not extract it.", file=sys.stderr)
    raise SystemExit(3)
archive_path.write_bytes(decoded)
PY

rm -rf "$TARGET_DIR/dataset_v4"
tar -xzf "$ARCHIVE" -C "$TARGET_DIR"
rm -f "$ARCHIVE"

echo "Extracted current data adapter to:"
echo "  $TARGET_DIR/dataset_v4"
echo
echo "Next:"
echo "  read $TARGET_DIR/dataset_v4/README.md"
