from utils import showTime

import mrtparse
import requests

from shutil import which
import os
import bz2
import subprocess
from typing import TextIO
from io import BytesIO
import json
from multiprocessing import Pool

def download_file(url: str) -> BytesIO:
    obj = BytesIO()
    r = requests.get(url, stream=True)
    r.raise_for_status()
    for chunk in r.iter_content(chunk_size=128):
        obj.write(chunk)
    obj.seek(0)
    return obj

def process_entry(entry: mrtparse.Reader) -> dict:
    if getattr(entry, 'err', None) is not None:
        raise Exception("{entry.err=} {entry.err_msg=} {entry.buf=}")
    entry = entry.data
    subtype = entry.get('subtype', [None, "None"])[0]
    if subtype == 1:
        metadata.update({ # pylint:disable=undefined-variable
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

def process_master_n(version: int) -> tuple:
    with showTime(f'download master{version}', print_until_finished=True):
        master_n = download_file(f'https://grc.jerryxiao.cc/master{version}_latest.mrt.bz2')
    with showTime(f'process master{version}', print_until_finished=True):
        metadata = globals()['metadata'] = dict()
        entries = list()
        for entry in mrtparse.Reader(bz2.BZ2File(master_n, 'rb')):
            processed = process_entry(entry)
            if processed is not None:
                entries.append(processed)
    return (metadata, entries)

with Pool(2) as pool:
    processed_4, processed_6 = pool.map(process_master_n, (4, 6))
metadata4, entries4 = processed_4
metadata6, entries6 = processed_6
entries = {"metadata": {"ipv4": metadata4, "ipv6": metadata6}, "ipv4": entries4, "ipv6": entries6}

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
            ret = self.p.returncode
            stderr = self.p.stderr.read()
            if ret or stderr:
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
