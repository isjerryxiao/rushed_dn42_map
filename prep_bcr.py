from mrt import process_master_n
from multiprocessing import Pool
from requests.exceptions import HTTPError

from mrtmap import gen_registry_info, asname, iter_path, calc_centrality, my_centrality, fullasmap as _fm

from datetime import date, timedelta
import csv

from utils import showTime

with showTime('load registry info'):
    gen_registry_info()

def short_asname(asn: int) -> str:
    name = asname(asn, allow_empty=True)
    if name:
        MAX_LENGTH = 11
        _ns = name.split()
        _ns = str(asn) if not _ns else _ns
        c = 0
        l_res = list()
        for s in _ns:
            l_res.append(s)
            if len(" ".join(l_res)) > MAX_LENGTH:
                l_res.pop(-1)
                break
        if not l_res:
            l_res = [_ns[0][:MAX_LENGTH]]
        res = " ".join(l_res)
        if not res:
            res = str(asn)
        else:
            res = f"{res} {asn:10d}"
    else:
        res = str(asn)
    return res

def get_centrality_for(mdate: date) -> dict:
    '''
        raises HTTPError
            HTTPError.response.status_code == 404
    '''
    with showTime('load path info', print_until_finished=True):
        with Pool(2) as pool:
            processed_4, processed_6 = pool.map(process_master_n, [f"{mdate.strftime('%Y/%m')}/master{version}_{mdate.strftime('%Y-%m-%d')}.mrt.bz2" for version in (4, 6)])
        _, entries4 = processed_4
        _, entries6 = processed_6
        for entry in [*entries4, *entries6]:
            for rib in entry["rib"]:
                try:
                    p = [int(i) for i in rib["as_path"]]
                except Exception:
                    print(rib)
                    raise
                iter_path(p)

    with showTime('calc centrality'):
        return my_centrality(_fm, *calc_centrality(_fm))

date_centrality = dict()
uniq_asns = set()

start_date = date(2021, 3, 27)
end_date = date.today()
#end_date = date(2021, 3, 29)

mdate = start_date
while mdate < end_date:
    print(f"[{(mdate - start_date) / (end_date - start_date) * 100: 3.2f}%] {mdate.strftime('%Y-%m-%d')}")
    try:
        centrality = get_centrality_for(mdate)
    except HTTPError as err:
        assert err.response.status_code == 404
        print(err)
        mdate += timedelta(days=1)
        continue
    uniq_asns = set.union(uniq_asns, centrality.keys())
    date_centrality[mdate] = {asn: c**4 for asn, c in centrality.items()}
    mdate += timedelta(days=1)

uniq_asns = tuple(uniq_asns)
with open('dumpbcr.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["date", *[short_asname(asn) for asn in uniq_asns]])
    for mdate, centrality in date_centrality.items():
        cdata = lambda: [centrality.get(asn, -1.0) for asn in uniq_asns]
        writer.writerow([mdate.strftime('%Y-%m-%d'), *cdata()])
