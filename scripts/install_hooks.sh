#!/usr/bin/env bash
#
# Installs the git hooks that live in `scripts/hooks`.
#
# The hooks are kept in the repository so they can be shared and reviewed, and
# they are activated by pointing `core.hooksPath` to that directory.
#
# Uninstall them with: git config --unset core.hooksPath

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HOOKS_DIR="scripts/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "No hooks directory found at $HOOKS_DIR" >&2
    exit 1
fi

while IFS= read -r -d '' hook; do
    chmod +x "$hook"
done < <(find "$HOOKS_DIR" -maxdepth 1 -type f -name '*' ! -name '*.sample' -print0)

git config core.hooksPath "$HOOKS_DIR"

echo "Installed the git hooks from $HOOKS_DIR"
echo "Remove them with: git config --unset core.hooksPath"
