from utils import showTime

from pathlib import Path
from math import sqrt
import json
import bz2

registry_info = dict()
def gen_registry_info() -> None:
    for f in Path('registry/data/aut-num').iterdir():
        if f.name.startswith("AS"):
            asn = int(f.name.removeprefix("AS"))
            assert asn not in registry_info
            info = registry_info[asn] = dict()
            raw = f.read_text()
            info['raw'] = raw
            info['name'] = list(filter(lambda x: "as-name:" in x, raw.split('\n')))[-1].removeprefix("as-name:").strip()

def asname(asn: int, allow_empty=False) -> str:
    try:
        return registry_info[asn]['name']
    except Exception:
        if allow_empty:
            return ""
        return f"No such as {asn}"
def asinfo(asn: int, allow_empty=False) -> str:
    try:
        return registry_info[asn]['raw']
    except Exception:
        if allow_empty:
            return ""
        return f"No such as {asn}"

asmap = dict()
fullasmap = dict()

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

def calc_centrality(fullasmap):
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

def my_centrality(fullasmap, closeness_centrality, betweenness_centrality):
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
        node_centrality.append((asn, size))
    node_centrality.sort(key=lambda x: x[1], reverse=True)
    return {k: v for k, v in node_centrality}

def main():
    with showTime('load registry info'):
        gen_registry_info()
        Path("registry.json").write_text(json.dumps(registry_info, separators=(',', ':')))

    with showTime('load path info'):
        with bz2.BZ2File("parsed.jsonl.bz2", 'r') as f:
            while line := f.readline():
                entry = json.loads(line)
                if entry["type"] in {"ipv4", "ipv6"}:
                    for rib in entry["rib"]:
                        try:
                            p = [int(i) for i in rib["as_path"]]
                        except Exception:
                            print(rib)
                            raise
                        iter_path(p)
                else:
                    assert entry["type"] == "metadata"

        assert asmap
        assert fullasmap

    with showTime('calc centrality'):
        closeness_centrality, betweenness_centrality = calc_centrality(fullasmap)
        node_centrality = my_centrality(fullasmap, closeness_centrality, betweenness_centrality)

    with showTime('dump isp.json'):
        dict_to_dump = dict()
        for idx, asn in enumerate(node_centrality.keys()):
            entry = {
                "asn": asn,
                "name": asname(asn),
                "peers": len(fullasmap[asn]),
                "centrality": node_centrality[asn],
                "rank": idx + 1,
                "closeness": closeness_centrality[asn],
                "betweenness": betweenness_centrality[asn]
            }
            dict_to_dump[asn] = entry
        to_dump = [v for v in dict_to_dump.values()]
        Path("isp.json").write_text(json.dumps(to_dump, indent=2))

    with showTime('gen index.html'):
        from pyvis.network import Network
        net = Network()
        net.path = "templates/template.html"
        net.width = net.height = "100%"

        def gentitle(asn):
            ret = list()
            ret.append(f"<p></p><div>AS{asn} {asname(asn)}</div>")
            ret.append(f"<div>rank: {dict_to_dump[asn]['rank']}</div>")
            ret.append(f"<div>centrality: {node_centrality[asn]:.4f}</div>")
            ret.append(f"<div>closeness: {closeness_centrality[asn]:.4f}</div>")
            ret.append(f"<div>betweenness: {betweenness_centrality[asn]:.4f}</div>")
            ret.append(f"<div>peer count: {len(fullasmap[asn])}</div>")
            ret.append(f"<p></p><div>Peer list:</div><p></p>")
            for peeras in fullasmap[asn]:
                ret.append(f"<div onclick=\"select_node({peeras});\">{asname(peeras)}</div>")
            ret.append("<p></p><div>Registry:</div>")
            _registry = asinfo(asn)#.replace("\n", "<br/>")
            ret.append(f"<pre>{_registry}</pre>")
            return "".join(ret)
        for asn, peers in fullasmap.items():
            size = node_centrality[asn]
            net.add_node(asn, label=asname(asn), size=size, title=gentitle(asn))
        for asn, peers in asmap.items():
            for p in peers:
                net.add_edge(asn, p)

        net.save_graph('index.html')

if __name__ == "__main__":
    main()
