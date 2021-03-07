#!/bin/bash
set -ex
[ -e registry ] && (cd registry; git pull) || git clone https://git.jerryxiao.cc/sync/dn42_registry.git registry --depth 1 --single-branch
[ -e grc.txt ] || ssh $HOST > grc.txt
[ -z "$CI" ] && {
python3 -m venv v
v/bin/pip install -r req.txt
v/bin/python map.py
} || python3 map.py
