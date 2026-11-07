#!/usr/bin/env bash
# Doorlopende dev-checks voor het datamodel (geen privébron nodig).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 model/tools/build_model.py --scan none --crop-out "" >/dev/null
python3 model/tools/build_tile_register.py --scans none >/dev/null
git diff --quiet -- model/data model/pilot/pilot_data.js || { echo "Dataset niet reproduceerbaar uit traces (diff)"; git --no-pager diff --stat -- model/data model/pilot/pilot_data.js; exit 1; }
python3 model/validate.py model/data/bg.v2.json
python3 -m unittest discover -s model/tests
