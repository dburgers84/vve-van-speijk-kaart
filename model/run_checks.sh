#!/usr/bin/env bash
# Doorlopende dev-checks voor het datamodel (geen privébron nodig).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 model/tools/build_model.py --scan none --crop-out "" >/dev/null
python3 model/tools/build_floor.py --floor 1e --scan none >/dev/null
python3 model/tools/build_floor.py --floor 2e --scan none >/dev/null
python3 model/tools/build_floor.py --floor 3e --scan none >/dev/null
python3 model/tools/build_floor.py --floor 4e --scan none >/dev/null
python3 model/tools/number_check.py >/dev/null
python3 model/tools/build_tile_register.py --scans none >/dev/null
git diff --quiet -- model/data model/pilot/pilot_data.js model/pilot/pilot_data_f1.js model/pilot/pilot_data_f2.js model/pilot/pilot_data_f3.js model/pilot/pilot_data_f4.js || { echo "Dataset niet reproduceerbaar uit traces (diff)"; git --no-pager diff --stat -- model/data model/pilot/pilot_data.js model/pilot/pilot_data_f1.js model/pilot/pilot_data_f2.js model/pilot/pilot_data_f3.js model/pilot/pilot_data_f4.js; exit 1; }
python3 model/validate.py model/data/bg.v2.json model/data/f1.v2.json model/data/f2.v2.json model/data/f3.v2.json model/data/f4.v2.json
python3 -m unittest discover -s model/tests
