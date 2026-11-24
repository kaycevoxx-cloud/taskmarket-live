#!/bin/sh
# One-command deploy: fetch fresh data, regenerate share images, rebuild
# the site, commit and push. GitHub Pages serves docs/ on the main branch.
set -e
cd "$(dirname "$0")"
python3 fetch.py
python3 gen_og.py
python3 build.py
git add -A
if git diff --cached --quiet; then
  echo "deploy: no changes to publish"
else
  git commit -m "Hourly data refresh: $(python3 -c "import json; print(json.load(open('docs/data.json'))['fetchedAt'])")"
  git push
  echo "deploy: pushed; live at https://kaycevoxx-cloud.github.io/taskmarket-live/"
fi
