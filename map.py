myas = [4242423618, 4201270006]

from pathlib import Path
from math import sqrt
import json

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

def calc_centrality():
    all_distance = dict()
    _betweenness = {k: 0.0 for k in fullasmap}
    for asn in fullasmap:
        distance = all_distance.setdefault(asn, dict())
        distance[asn] = 0
        queue = [asn]
        _search_order = list()
        _path_via = {k: list() for k in fullasmap}
        _sigma = {k: 0 for k in fullasmap}
        _delta = {k: 0.0 for k in fullasmap}
        _sigma[asn] += 1
        while queue:
            item = queue.pop(0)
            _search_order.append(item)
            for nbr in fullasmap[item]:
                if nbr not in distance:
                    distance[nbr] = distance[item] + 1
                    queue.append(nbr)
                if distance[nbr] == distance[item] + 1:
                    _sigma[nbr] += _sigma[item]
                    _path_via[nbr].append(item)
        while _search_order:
            item = _search_order.pop(-1)
            _coeff = (1.0 + _delta[item]) / _sigma[item]
            for _ups in _path_via[item]:
                _delta[_ups] += _sigma[_ups] * _coeff
            if item != asn:
                _betweenness[item] += _delta[item]
    _maplen = len(fullasmap)
    _scale = 1.0 / ((_maplen - 1) * (_maplen - 2))
    _betweenness = [(k, v * _scale) for k, v in _betweenness.items()]
    _betweenness.sort(key=lambda x: x[1], reverse=True)
    _betweenness = {k: v for k, v in _betweenness}
    closeness = list()
    for asn, dis in all_distance.items():
        assert len(all_distance) == len(dis)
        closeness.append((asn, (len(all_distance) - 1) / sum(dis.values())))
    closeness.sort(key=lambda x: x[1], reverse=True)
    closeness = {k: v for k, v in closeness}
    return (closeness, _betweenness)

closeness_centrality, betweenness_centrality = calc_centrality()

def my_centrality():
    node_centrality = list()
    """ should be within 10 - 30 """
    mmin = 10.0
    mmax = 30.0
    clmin = min(closeness_centrality.values())
    clmax = max(closeness_centrality.values())
    bemin = min([v**0.25 for v in betweenness_centrality.values()])
    bemax = max([v**0.25 for v in betweenness_centrality.values()])
    clcalc = lambda x: ((mmax-mmin)/(clmax-clmin)*(x-clmin) + mmin)
    becalc = lambda x: ((mmax-mmin)/(bemax-bemin)*(x-bemin) + mmin)
    for asn in fullasmap:
        cl = closeness_centrality[asn]
        be = betweenness_centrality[asn] ** 0.25
        cl = clcalc(cl)
        be = becalc(be)
        size = 0.5 * (be + cl)
        print(be, cl, size)
        node_centrality.append((asn, size))
    node_centrality.sort(key=lambda x: x[1], reverse=True)
    return {k: v for k, v in node_centrality}
node_centrality = my_centrality()

dict_to_dump = dict()
for idx, asn in enumerate(node_centrality.keys()):
    entry = {
        "asn": asn,
        "name": asname(asn),
        "centrality": node_centrality[asn],
        "rank": idx + 1,
        "closeness": closeness_centrality[asn],
        "betweenness": betweenness_centrality[asn]
    }
    dict_to_dump[asn] = entry
to_dump = [v for v in dict_to_dump.values()]
Path("isp.json").write_text(json.dumps(to_dump, indent=2))

from pyvis.network import Network
net = Network()
net.path = "templates/template.html"
net.width = net.height = "100%"

def gentitle(asn):
    ret = list()
    ret.append(f"<p></p><div>AS{asn} {asname(asn)}</div>")
    ret.append(f"<div>rank: {dict_to_dump[asn]['rank']}</div>")
    ret.append(f"<div>centrality: {node_centrality[asn]:.2f}</div>")
    ret.append(f"<div>closeness: {closeness_centrality[asn]:.2f}</div>")
    ret.append(f"<div>betweenness: {betweenness_centrality[asn]:.2f}</div>")
    ret.append(f"<div>peer count: {len(fullasmap[asn])}</div>")
    ret.append(f"<p></p><div>Peer list:</div><p></p>")
    for peeras in fullasmap[asn]:
        ret.append(f"<div onclick=\"select_node({peeras});\">{asname(peeras)}</div>")
    ret.append("<p></p><div>Registey:</div>")
    _registry = asinfo(asn)#.replace("\n", "<br/>")
    ret.append(f"<pre>{_registry}</pre>")
    return "".join(ret)
for asn, peers in fullasmap.items():
    #size = sqrt(sqrt(len(peers)+1)) * 10
    size = node_centrality[asn]
    net.add_node(asn, label=asname(asn), size=size, title=gentitle(asn))
for asn, peers in asmap.items():
    for p in peers:
        net.add_edge(asn, p)

net.save_graph('index.html')
