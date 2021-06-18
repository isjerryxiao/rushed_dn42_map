from datetime import date, timedelta, datetime
import csv

from typing import Tuple
from traceback import print_exc

from utils import showTime

with open('dumpbcr.csv', 'r', newline='') as csvfile, open('dumpbcr.csv.interpolated', 'w', newline='') as rcsvfile:
    reader = csv.reader(csvfile)
    writer = csv.writer(rcsvfile)
    writer.writerow(next(reader))
    INTERPOLATE_STEPS = 10
    rows = [r for r in reader]
    def process_row(row: list) -> Tuple[date, list]:
        mdate, *vals = row
        vals = [float(i) for i in vals]
        mdate = datetime.strptime(mdate, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        return (mdate, vals)
    def linear_interpolate(start, end) -> list:
        ret = list()
        step = (end - start) / INTERPOLATE_STEPS
        for i in range(INTERPOLATE_STEPS-1):
            ret.append(start + i*step)
        #ret.append(end)
        return ret
    result = list()
    for i in range(len(rows)-1):
        result_yx = list()
        o1, o2 = map(process_row, [rows[i], rows[i+1]])
        date1, data1 = o1
        date2, data2 = o2
        result_yx.append(linear_interpolate(date1, date2))
        assert len(data1) == len(data2)
        for j in range(len(data1)):
            result_yx.append(linear_interpolate(data1[j], data2[j]))
        result.extend(list(map(list, zip(*result_yx))))
    datem1, datam1 = process_row(rows[-1])
    result.append([datem1, *datam1])
    for l in result:
        print(l)
        writer.writerow([l[0].strftime('%Y-%m-%d %H:%M:%S'), *l[1:]])
