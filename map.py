myas = [4242423618, 4201270006]

from pathlib import Path

asname_cache = dict()
def asname(asn: int) -> str:
    try:
        if not (name := asname_cache.get(asn)):
            ln = list(filter(lambda x: "as-name:" in x, Path(f'registry/data/aut-num/AS{asn}').read_text().split('\n')))[-1]
            name = ln.removeprefix("as-name:").strip()
        return asname_cache.setdefault(asn, name)
    except Exception:
        return "NULL"
def asinfo(asn: int) -> str:
    try:
        return Path(f'registry/data/aut-num/AS{asn}').read_text()
    except Exception:
        return "NULL"

source = Path('grc.txt').read_text()

asmap = dict()
fullasmap = dict()

for line in source.split('\n'):
    if not "BGP.as_path:" in line:
        continue
    line = line.strip()
    if not line:
        continue
    path = line.removeprefix('BGP.as_path: ').split()
    try:
        path = [int(i) for i in path if i]
    except Exception:
        print("path", path, "is garbage")
        continue

    def iter_path(p):
        for idx in range(len(p)-1):
            as1, as2 = p[idx:idx+2]
            if as1 == as2:
                continue
            if as2 in asmap.get(as1, set()):
                continue
            if as1 in asmap.get(as2, set()):
                continue
            fullasmap.setdefault(as1, set()).add(as2)
            fullasmap.setdefault(as2, set()).add(as1)
            asmap.setdefault(as1, set()).add(as2)
#    for _as in myas:
#        p = path.copy()
#        p.insert(0, _as)
#        iter_path(p)
    iter_path(path)

assert asmap
assert fullasmap

from pyvis.network import Network
net = Network()
net.path = "templates/template.html"
net.width = net.height = "100%"

def gentitle(asn):
    ret = list()
    ret.append(f"<div>AS{asn} {asname(asn)}</div>")
    for i in asinfo(asn).split("\n"):
        ret.append(f"<div>{i}</div>")
    ret.append(f"<br/><div>Peers: {len(fullasmap[asn])}</div><br/>")
    for peeras in fullasmap[asn]:
        ret.append(f"<div onclick=\"select_node({peeras});\">{asname(peeras)}</div>")
    return "".join(ret)
from math import sqrt
for asn, peers in fullasmap.items():
    size = sqrt(sqrt(len(peers)+1)) * 10
    net.add_node(asn, label=asname(asn), size=size, title=gentitle(asn))
for asn, peers in asmap.items():
    for p in peers:
        net.add_edge(asn, p)

net.save_graph('index.html')
