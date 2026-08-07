#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE_DIR="$ROOT/archive"
ARCHIVE="$ARCHIVE_DIR/graphedit_r1_source.tar.gz"
EXPECTED="7e254475cc57448bafdbaa89da446ab8cbd68e157fdc72689e784a3f8d116af2"

python3 - "$ARCHIVE_DIR" "$ARCHIVE" "$EXPECTED" <<'PY'
from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

archive_dir = Path(sys.argv[1])
archive_path = Path(sys.argv[2])
expected = sys.argv[3].strip().lower()
parts = sorted(archive_dir.glob("graphedit_r1_source.tar.gz.b64.part*"))

if not parts:
    raise SystemExit(f"ERROR: archive parts not found under {archive_dir}")

alphabet = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
whitespace = set(b" \t\r\n\v\f")
chunks: list[bytes] = []
non_base64: list[tuple[str, int, list[int]]] = []

for part in parts:
    raw = part.read_bytes()
    bad = [value for value in raw if value not in alphabet and value not in whitespace]
    if bad:
        non_base64.append((part.name, len(bad), sorted(set(bad))[:20]))
    clean = bytes(value for value in raw if value in alphabet)
    chunks.append(clean)
    print(
        f"[GraphEdit-R1] {part.name}: raw={len(raw)} clean={len(clean)} "
        f"mod4={len(clean) % 4} non_base64={len(bad)}"
    )

encoded = b"".join(chunks)
print(f"[GraphEdit-R1] joined_base64_bytes={len(encoded)} mod4={len(encoded) % 4}")

if non_base64:
    print("[GraphEdit-R1][WARN] Non-Base64 bytes were found and filtered:", file=sys.stderr)
    for name, count, values in non_base64:
        print(f"  {name}: count={count}, byte_values={values}", file=sys.stderr)

try:
    decoded = base64.b64decode(encoded, validate=True)
except Exception as exc:
    print(f"ERROR: Python Base64 decoding failed: {exc}", file=sys.stderr)
    print("This indicates the committed Base64 stream itself is malformed.", file=sys.stderr)
    raise SystemExit(2)

actual = hashlib.sha256(decoded).hexdigest()
print(f"[GraphEdit-R1] decoded_bytes={len(decoded)}")
print(f"[GraphEdit-R1] sha256={actual}")

if actual != expected:
    print("ERROR: SHA-256 mismatch", file=sys.stderr)
    print(f"expected: {expected}", file=sys.stderr)
    print(f"actual:   {actual}", file=sys.stderr)
    print("The committed archive content is corrupted; do not extract it.", file=sys.stderr)
    raise SystemExit(3)

archive_path.write_bytes(decoded)
PY

rm -rf "$ROOT/source"
tar -xzf "$ARCHIVE" -C "$ROOT"
rm -f "$ARCHIVE"

echo "GraphEdit-R1 extracted successfully."
echo "Source: $ROOT/source"
echo "Read:   $ROOT/source/README.md"
