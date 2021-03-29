#!/bin/bash
set -ex
[ -e registry ] && (cd registry; git pull) || git clone https://git.jerryxiao.cc/sync/dn42_registry.git registry --depth 1 --single-branch
[ -e parsed.jsonl.bz2 ] && rm parsed.jsonl.bz2
if [ -z "$CI" ]; then
    python3 -m venv v
    v/bin/pip install -r req.txt
    v/bin/python mrt.py
    v/bin/python map.py
else
    python3 mrt.py
    python3 map.py
fi
