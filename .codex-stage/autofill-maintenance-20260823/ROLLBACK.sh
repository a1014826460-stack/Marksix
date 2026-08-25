#!/bin/sh
set -eu
target="${1:?rollback target copy required}"
original="${target}.original"
test -f "$original"
cp "$original" "$target"
cmp -s "$original" "$target"
printf '%s\n' "rollback restored: $target"
printf '%s\n' "MODIFIED_FILE remains changed: MODIFIED_FILE.txt"
