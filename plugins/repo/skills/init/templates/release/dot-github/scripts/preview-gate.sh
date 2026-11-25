#!/usr/bin/env bash
# Decides whether a preview is worth publishing, for any registry, without
# querying any: compares the package inputs listed in .github/preview-inputs
# (one path per line, written by the modules present) between HEAD and the
# commit of the last successful deployment of the `preview` environment, read
# from GitHub's deployments API.
#
# Needs GH_TOKEN with `deployments: read`, and a full clone (fetch-depth: 0).
# Writes publish=true|false and base=<commit or empty> to $GITHUB_OUTPUT.
# Any failed lookup fails the run rather than guessing.
set -euo pipefail

inputs_file=.github/preview-inputs
mapfile -t inputs < <(sed -e 's/#.*//' -e 's/[[:space:]]*$//' -e '/^$/d' "$inputs_file")
if (( ${#inputs[@]} == 0 )); then
  echo "::error::$inputs_file lists no path."
  exit 1
fi

base=""
deployments=$(gh api "repos/$GITHUB_REPOSITORY/deployments?environment=preview&per_page=30" \
  --jq '.[] | "\(.id) \(.sha)"')
while read -r id sha; do
  [[ -n "${id:-}" ]] || continue
  state=$(gh api "repos/$GITHUB_REPOSITORY/deployments/$id/statuses?per_page=1" --jq '.[0].state // ""')
  if [[ "$state" == "success" ]]; then
    base=$sha
    break
  fi
done <<< "$deployments"

if [[ -z "$base" ]]; then
  echo "No successful preview yet: publish."
  publish=true
elif ! git cat-file -e "${base}^{commit}" 2> /dev/null; then
  echo "::warning::The last preview was built from $base, which this history does not contain: publish."
  publish=true
elif git diff --quiet "$base" HEAD -- "${inputs[@]}"; then
  echo "Nothing that ships changed since the last preview ($base): nothing to publish." | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
  publish=false
else
  echo "Package inputs changed since the last preview ($base):"
  git diff --stat "$base" HEAD -- "${inputs[@]}"
  publish=true
fi

{
  echo "publish=$publish"
  echo "base=$base"
} >> "${GITHUB_OUTPUT:-/dev/stdout}"
