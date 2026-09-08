#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/bin"
TARGET="$TARGET_DIR/obs"

mkdir -p "$TARGET_DIR"
chmod +x "$ROOT_DIR/bin/obs"
ln -sfn "$ROOT_DIR/bin/obs" "$TARGET"

echo "Installed obs at $TARGET"
if ":$PATH:" != *":$TARGET_DIR:"* ]]; then
  echo "Add this to your shell profile, then open a new terminal:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
echo "Next: obs setup /path/to/your-vault && obs init"
