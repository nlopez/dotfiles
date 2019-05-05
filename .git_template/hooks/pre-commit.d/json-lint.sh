#!/usr/bin/env bash
# Runs all .json or .js files through pythons json lint tool before commiting,
# to make sure that you don't commit broken json objects.

git_dir=$(git rev-parse --show-toplevel)

function get_files() {
  git diff-index -z --name-only --diff-filter=ACM --cached HEAD -- \
  | grep -E '.*\.(json|js)$'
}

while read -r -d $'\0'; do
  if ! python -mjson.tool "$REPLY" 2> /dev/null ; then
    echo "Lint check of JSON object failed. Your changes were not commited."
    echo "in $git_dir/$REPLY:"
    python -mjson.tool "$REPLY"
    exit 1
  fi
done < <(get_files)
