import mrtparse
import requests

from time import time
from shutil import which
import os
import bz2
import subprocess
from typing import TextIO
from io import BytesIO
import json
import itertools

reqs = requests.Session()

def download_file(url: str) -> BytesIO:
    obj = BytesIO()
    r = reqs.get(url, stream=True)
    r.raise_for_status()
    for chunk in r.iter_content(chunk_size=128):
        obj.write(chunk)
    obj.seek(0)
    return obj

entries = {"metadata": list(), "ipv4": list(), "ipv6": list()}

def process_entry(entry: mrtparse.Reader) -> dict:
    if getattr(entry, 'err', None) is not None:
        raise Exception("{entry.err=} {entry.err_msg=} {entry.buf=}")
    parsed = dict()
    entry = entry.data
    subtype = entry.get('subtype', [None, "None"])[0]
    if subtype == 1:
        entries['metadata'].append({
            'timestamp': entry['timestamp'][0],
            'time': entry['timestamp'][1],
        })
        return None
    elif subtype in {2, 8, 4, 10}:
        cidr = f"{entry['prefix']}/{entry['prefix_length']}"
        rib = list()
        for rib_entry in entry['rib_entries']:
            rib_attr = dict()
            rib.append(rib_attr)
            for attr in rib_entry['path_attributes']:
                attr_type = attr['type'][0]
                if attr_type == 2:
                    assert len(attr['value']) == 1
                    rib_attr['as_path'] = attr['value'][0]['value']
                elif attr_type == 8:
                    rib_attr['community'] = attr['value']
                elif attr_type == 16:
                    rib_attr['extended_community'] = attr['value']
                elif attr_type == 32:
                    rib_attr['large_community'] = attr['value']
                elif attr_type in {1, 3, 4, 5, 6, 7, 14}:
                    pass
                else:
                    print(f"unknown {attr_type=} {attr['type'][1]}")
            rib.append(rib_attr)
        return {
            "prefix": cidr,
            "rib": rib,
        }
    else:
        print(f"unknown {subtype=}")
        return None

class showTime:
    def __init__(self, *args) -> None:
        print(*args, end=' ', flush=True)
    def __enter__(self) -> None:
        self.__start = time()
    def __exit__(self, *_) -> None:
        self.__end = time()
        print(f"{self.__end - self.__start:.2f}s")

with showTime('download master4'):
    master4 = download_file('https://grc.jerryxiao.cc/master4_latest.mrt.bz2')
with showTime('download master6'):
    master6 = download_file('https://grc.jerryxiao.cc/master6_latest.mrt.bz2')

with showTime('process master4'):
    for entry in mrtparse.Reader(bz2.BZ2File(master4, 'rb')):
        assert getattr(entry, 'err', None) is None
        processed = process_entry(entry)
        if processed is not None:
            entries["ipv4"].append(processed)
with showTime('process master6'):
    for entry in mrtparse.Reader(bz2.BZ2File(master6, 'rb')):
        assert getattr(entry, 'err', None) is None
        processed = process_entry(entry)
        if processed is not None:
            entries["ipv6"].append(processed)

entries["metadata"] = dict(zip(["ipv4", "ipv6"], entries["metadata"]))

class subprocessBzip2:
    def __init__(self, fname: os.PathLike, *_) -> None:
        self.fname = fname
    def __enter__(self) -> TextIO:
        self.f = open(self.fname, 'w')
        self.p = subprocess.Popen(['bzip2', '--best', '--compress', '--stdout'], stdin=subprocess.PIPE, stdout=self.f, stderr=subprocess.PIPE, encoding='utf-8')
        return self.p.stdin
    def __exit__(self, *_) -> None:
        try:
            self.p.stdin.flush()
            self.p.stdin.close()
            self.p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            self.p.wait()
        finally:
            self.f.close()
            if (ret := self.p.returncode) or (stderr := self.p.stderr.read()):
                print(f"{ret=} {stderr=}")

with showTime('dump jsonl'):
    if which("bzip2") is None:
        compressor = bz2.open
    else:
        compressor = subprocessBzip2
    with compressor('parsed.jsonl.bz2', 'wt') as f:
        for entry_type, entry_val in entries.items():
            if isinstance(entry_val, dict):
                json.dump({"type": entry_type, **entry_val}, f, separators=(',', ':'))
                f.write('\n')
            else:
                assert isinstance(entry_val, list)
                for entry in entry_val:
                    json.dump({"type": entry_type, **entry}, f, separators=(',', ':'))
                    f.write('\n')
