"""Convert an EnergyPlus TMY3 weather file (.epw, plus its .stat for the ASHRAE design
conditions) into the compact JSON the Property App's energy model reads.

    python3 build/tools/epw_to_json.py WEATHER.epw WEATHER.stat property/data/weather-tmy3.json "Source URL"
"""
import csv, json, re, sys


def design(stat_path):
    txt = open(stat_path, encoding='latin-1').read()
    heat = re.search(r'\tHeating\t(.+)', txt).group(1).split('\t')
    cool = re.search(r'\tCooling\t(.+)', txt).group(1).split('\t')
    f = lambda v: float(v)
    return dict(source='Climate Design Data 2009 ASHRAE Handbook',
                heating=dict(coldestMonth=int(heat[0]), db996C=f(heat[1]), db990C=f(heat[2])),
                cooling=dict(hottestMonth=int(cool[0]), dailyRangeC=f(cool[1]), db004C=f(cool[2]), mcwb004C=f(cool[3]), db010C=f(cool[4]), mcwb010C=f(cool[5])))


def main(epw, stat, out, source):
    rows = list(csv.reader(open(epw, encoding='latin-1')))
    loc = rows[0]
    data = [r for r in rows[8:] if len(r) > 20]
    assert len(data) == 8760, len(data)
    col = lambda i, cast=float: [cast(r[i]) for r in data]
    res = dict(station=f"{' '.join(loc[1].split())}, {loc[2]} (WMO {loc[5]})", dataset=loc[4], source=source,
               lat=float(loc[6]), lon=float(loc[7]), tz=int(float(loc[8])), elevM=float(loc[9]), design=design(stat),
               units=dict(t='C', ws='m/s', ghi='Wh/m2', dni='Wh/m2', dhi='Wh/m2'),
               hourly=dict(t=col(6), ws=col(21), ghi=col(13, int), dni=col(14, int), dhi=col(15, int)))
    with open(out, 'w') as fh: json.dump(res, fh, separators=(',', ':'))
    print(out, res['station'], 'min', min(res['hourly']['t']), 'max', max(res['hourly']['t']))


if __name__ == '__main__':
    main(*sys.argv[1:5])
