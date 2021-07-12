from mrt import process_master_n
from multiprocessing import Pool, cpu_count
from requests.exceptions import HTTPError, ConnectionError

from mrtmap import gen_registry_info, asname, iter_path, calc_centrality, my_centrality, fullasmap as _fm

from datetime import date, timedelta
import csv

from traceback import print_exc

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
    with showTime(f"load path info {mdate.strftime('%Y-%m-%d')}", print_until_finished=True):
        processed_4, processed_6 = map(process_master_n, [f"{mdate.strftime('%Y/%m')}/master{version}_{mdate.strftime('%Y-%m-%d')}.mrt.bz2" for version in (4, 6)])
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

    with showTime(f"calc centrality {mdate.strftime('%Y-%m-%d')}", print_until_finished=True):
        return my_centrality(_fm, *calc_centrality(_fm))

uniq_asns = set()

start_date = date(2021, 3, 27)
end_date = date.today()
#end_date = date(2021, 3, 29)

dates = list()
mdate = start_date
while mdate < end_date:
    dates.append(mdate)
    mdate += timedelta(days=1)

def w_get_centrality_for(mdate):
    while True:
        print(f"[{(mdate - start_date) / (end_date - start_date) * 100: 3.2f}%] {mdate.strftime('%Y-%m-%d')}")
        try:
            centrality = get_centrality_for(mdate)
            centrality = {asn: c**4 for asn, c in centrality.items()}
            return centrality
        except ConnectionError:
            print_exc()
            continue
        except HTTPError as err:
            assert err.response.status_code == 404
            print(err)
        except Exception:
            print_exc()
        return None

with Pool(cpu_count()) as pool:
    results = pool.map(w_get_centrality_for, dates)
    d_results = dict(zip(dates, results))

    for k in d_results.copy():
        if d_results[k] is None:
            d_results.pop(k)
            #d_results[k] = d_results[k - timedelta(days=1)]
for centrality in d_results.values():
    uniq_asns = set.union(uniq_asns, centrality.keys())

uniq_asns = tuple(uniq_asns)
with open('dumpbcr.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["date", *[short_asname(asn) for asn in uniq_asns]])
    for mdate, centrality in d_results.items():
        cdata = lambda: [centrality.get(asn, -1.0) for asn in uniq_asns]
        writer.writerow([mdate.strftime('%Y-%m-%d'), *cdata()])
