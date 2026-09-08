#!/usr/bin/env bash
# Friendly, non-mutating setup diagnostics.

doctor() {
  local problems=0

  echo "Obsidian Research OS doctor"
  if [[ -n "$VAULT_PATH" && -d "$VAULT_PATH" ]]; then
    echo "  ✓ Vault: $VAULT_PATH"
  else
    echo "  ✗ Vault: not configured (run: obs setup /path/to/vault)"
    problems=$((problems + 1))
  fi

  if command -v python3 >/dev/null 2>&1; then
    echo "  ✓ Python: $(python3 --version 2>&1)"
  else
    echo "  ✗ Python 3: not found"
    problems=$((problems + 1))
  fi

  if python3 -c 'import tkinter' >/dev/null 2>&1; then
    echo "  ✓ Focus window: ready"
  else
    echo "  ! Focus window: Tkinter is missing (install python3-tk to use obs focus)"
  fi

  if command -v "$OBSIDIAN_CMD" >/dev/null 2>&1; then
    echo "  ✓ Obsidian CLI: $OBSIDIAN_CMD"
  else
    echo "  ! Obsidian CLI: '$OBSIDIAN_CMD' not found (needed for opening, search, capture, and papers)"
  fi

  if command -v git >/dev/null 2>&1; then
    echo "  ✓ Git: $(git --version | head -n 1)"
  else
    echo "  ! Git: not found (only needed for obs backup)"
  fi

  if [[ -x "$BASE_DIR/.venv/bin/python" ]]; then
    echo "  ✓ Calendar environment: ready"
  else
    echo "  ! Calendar environment: optional; create with python3 -m venv .venv"
  fi

  if [[ -n "$VAULT_PATH" && -d "$VAULT_PATH" ]]; then
    local template missing=0
    for template in Daily.md Research.md Paper.md Inbox.md; do
      if [[ ! -f "$VAULT_PATH/Templates/$template" ]]; then
        missing=1
      fi
    done
    if [[ $missing -eq 0 ]]; then
      echo "  ✓ Vault templates: ready"
    else
      echo "  ! Vault templates: missing one or more (run: obs init)"
    fi
  fi

  if [[ $problems -eq 0 ]]; then
    printf '\nCore setup looks good. Items marked ! are optional.\n'
  else
    printf '\nFix the items marked ✗, then run obs doctor again.\n'
    return 1
  fi
}
