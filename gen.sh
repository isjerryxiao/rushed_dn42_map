#!/bin/bash
set -ex
python3 -m venv v
v/bin/pip install -r req.txt
[ -e registry ] && (cd registry; git pull) || git clone https://git.jerryxiao.cc/sync/dn42_registry.git registry --depth 1 --single-branch
echo show r all table master4 table master6 |ssh -J $HOST shell@fd42:4242:2601:ac12::1 > grc.txt
v/bin/python map.py
