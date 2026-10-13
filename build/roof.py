"""Roof framing: a truss layout read from the owner's A-2, for pricing, the 3D model and the truss designer.

A-2 gives the pitches (6:12 main hips, 4:12 vault over kitchen and living, 6:12 vaulted patio ceiling, 2:12 porch
shed, 8:12 front gables) and the hip and ridge lines, but no truss layout. This lays one out the usual way:

  A  main roof over the great room and the bedroom wing: trusses span front to rear at 24" o.c., ridge on the
     A-2 ridge line (Y 29.4), hip end over the bedroom wing (stepped hip trusses), scissor trusses with a 4:12
     bottom chord over the kitchen and living vault, tall-end trusses where the rear wall steps in at the patio.
  G1 a two-ply girder truss on the line between the master wing and the kitchen (X 30.75): the master wing and
     garage trusses hang from it, so the wall under it stays a non-bearing partition.
  B  master wing and C its rear bump-out, D the garage: trusses span side to side (X), hip ends per A-2.
  PR the patio: 2x10 rafters on a ridge beam and side beams, the 6:12 ceiling on the rafters.
  PO the porch: 2x8 rafters at 2:12 from the front wall to a beam on the posts.

Heights are above the slab. Every truss is a draft: the truss maker designs the real ones (loads, webs, girders,
hip and valley sets, the 8:12 front gables, which are over-framed on the main trusses and not drawn here).
"""
import math
from setlib import HOUSE, ft_in

CEIL = HOUSE['meta']['ceiling_ft']
P = 6 / 12            # main pitch
HEEL = 1.0            # 12" raised (energy) heel: full R-49 attic insulation out to the wall line
OH = 1.5              # eave overhang, A-2
OC = 2.0              # 24" o.c.
TOP, BOT, WEB = 5.5 / 12, 3.5 / 12, 3.5 / 12
VAULT = 4 / 12
RIDGE_Y = 29.4        # A-2's main ridge line

AREAS = [
    dict(key='A', name='Main roof (great room, bedroom wing)', span='y', s=(30.75, 83.44), e=(5.08, 53.733), hip=(None, 83.44), girder=True),
    dict(key='B', name='Master wing', span='x', s=(5.08, 34.133), e=(5.373, 30.75), hip=(5.08, None)),
    dict(key='C', name='Master bedroom bump-out', span='x', s=(0.0, 5.08), e=(16.0, 31.0), hip=(0.0, None)),
    dict(key='D', name='Garage', span='x', s=(34.133, 70.093), e=(0.0, 30.75), hip=(34.133, 70.093)),
]


def _intervals(poly, axis, s):
    """Where the line (x = s if axis == 'y', else y = s) runs inside the polygon, as [(a0, a1)] along the other axis."""
    hits = []
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        if axis == 'y':   # vertical line x = s, crossings give y
            if (x0 > s) != (x1 > s): hits.append(y0 + (s - x0) * (y1 - y0) / (x1 - x0))
        else:
            if (y0 > s) != (y1 > s): hits.append(x0 + (s - y0) * (x1 - x0) / (y1 - y0))
    hits.sort()
    return [(hits[i], hits[i + 1]) for i in range(0, len(hits) - 1, 2)]


def bearing(area, s):
    """Bearing line to bearing line for a truss at station s, inside the area's eave lines (house + garage outline)."""
    ivs = _intervals(HOUSE['envelope'], area['span'], s) + _intervals(HOUSE['garage_outline'], area['span'], s)
    ivs.sort()
    merged = []
    for a, b in ivs:
        if merged and a <= merged[-1][1] + 0.05: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    e0, e1 = area['e']
    best = None
    for a, b in merged:
        a, b = max(a, e0), min(b, e1)
        if b - a > 2 and (best is None or b - a > best[1] - best[0]): best = (a, b)
    return best


def vault_at(s, a):
    """The 4:12 vault over kitchen and living: bottom chord rise above the plate at plan (s, a) for main trusses."""
    for rid in HOUSE['meta']['vault']['rooms']:
        r = next(r for r in HOUSE['rooms'] if r['id'] == rid)
        xs = [p[0] for p in r['poly']]; ys = [p[1] for p in r['poly']]
        if min(xs) <= s <= max(xs) and min(ys) <= a <= max(ys):
            return VAULT * min(a - min(ys), max(ys) - a), (min(ys), max(ys))
    return 0.0, None


def truss(area, s, girder=False):
    e0, e1 = area['e']
    b = bearing(area, s)
    if not b: return None
    b0, b1 = b
    cap = math.inf
    h0, h1 = area['hip']
    if h0 is not None: cap = min(cap, HEEL + P * max(0.0, s - h0))
    if h1 is not None: cap = min(cap, HEEL + P * max(0.0, h1 - s))
    top = lambda a: min(HEEL + P * min(a - e0, e1 - a), cap)
    # the top chord, from the tail of one overhang to the other (no overhang where the bearing is inside the eave line)
    t0 = b0 - OH if b0 - e0 < 0.3 else b0
    t1 = b1 + OH if e1 - b1 < 0.3 else b1
    ridge = (e0 + e1) / 2
    pts = sorted({t0, t1, min(max(ridge, b0), b1)} | ({e0 + (cap - HEEL) / P, e1 - (cap - HEEL) / P} if cap < math.inf else set()))
    pts = [a for a in pts if t0 <= a <= t1]
    m = []
    for a, c in zip(pts, pts[1:]):
        if c - a > 0.05: m.append((a, CEIL + top(a), c, CEIL + top(c), TOP))
    # bottom chord: flat at the plate, or 4:12 scissor in the vault
    vault = area['key'] == 'A' and not girder and vault_at(s, (b0 + b1) / 2)[1]
    bot = (lambda a: min(vault_at(s, a)[0], top(a) - 1.5)) if vault else (lambda a: 0.0)
    bpts = [b0, b1]
    if vault:
        v0, v1 = vault
        bpts = sorted({b0, b1, max(b0, v0), min(b1, v1), max(b0, min(b1, (v0 + v1) / 2))})
    for a, c in zip(bpts, bpts[1:]):
        if c - a > 0.05: m.append((a, CEIL + BOT / 2 + bot(a), c, CEIL + BOT / 2 + bot(c), BOT))
    # webs: end verticals, then a zigzag at panel points (a double-Fink-like pattern; the truss maker sets the real one)
    span = b1 - b0
    n = max(2, 2 * round(span / 14))
    pp = [b0 + i * span / n for i in range(n + 1)]
    for a in (b0, b1):
        if top(a) - bot(a) > 0.3: m.append((a, CEIL + bot(a), a, CEIL + top(a), WEB))
    if max(top(a) - bot(a) for a in pp) > 0.8:
        for i in range(n):
            a, c = pp[i], pp[i + 1]
            lo_a, lo_c = bot(a) + BOT, bot(c) + BOT
            if i % 2 == 0: m.append((a, CEIL + lo_a, c, CEIL + top(c) - 0.1, WEB))
            else: m.append((a, CEIL + top(a) - 0.1, c, CEIL + lo_c, WEB))
        if top(ridge) - bot(ridge) > 1 and b0 < ridge < b1: m.append((ridge, CEIL + bot(ridge), ridge, CEIL + top(ridge), WEB))
    peak = max(top(a) for a in pts)
    kind = 'girder' if girder else 'scissor' if vault else 'hip' if cap < HEEL + P * (ridge - e0) - 0.05 else 'common'
    tall = (b0 - e0 > 0.3 and top(b0) - HEEL > 0.3) or (e1 - b1 > 0.3 and top(b1) - HEEL > 0.3)
    return dict(axis=area['span'], s=round(s, 3), b=(round(b0, 3), round(b1, 3)), kind=kind, tall=tall, peak=peak,
                members=[[round(v, 3) for v in mm] for mm in m])


def stations(s0, s1, first=None):
    out = [first if first is not None else s0 + 0.0625]
    while out[-1] + OC < s1 - 0.0625: out.append(round(out[-1] + OC, 3))
    out.append(round(s1 - 0.0625, 3))
    return out


def rafters():
    """Patio and porch: rafters and beams, not trusses."""
    out, beams = [], []
    # patio: 2x10 rafters at 6:12 from the side beams (on the corner posts, X 43.79 and 64.21) to a ridge beam on X 54,
    # bird's-mouth on the beams, the vaulted ceiling on the rafters; gable at the rear (Y 0)
    x0, x1 = 43.79, 64.21; xr = (x0 + x1) / 2; R = 9.25 / 12
    for s in stations(0.21, 16.387):
        m = [(x0 - OH, CEIL - P * OH + R / 2, xr, CEIL + P * (xr - x0) + R / 2, R), (xr, CEIL + P * (xr - x0) + R / 2, x1 + OH, CEIL - P * OH + R / 2, R)]
        out.append(dict(axis='x', s=s, b=(x0, x1), kind='rafter', area='PR', members=[[round(v, 3) for v in mm] for mm in m]))
    rh = CEIL + P * (xr - x0)
    beams += [dict(name='Patio ridge beam', text=f'Patio ridge beam: 3-1/2" x 11-7/8" LVL on X {xr:.1f}, from the rear gable to the main roof, posts at each end (engineer to size). Rafters hang on it with LUS hangers; the 6:12 ceiling runs up to it.',
                   box=[xr - 0.146, 0.21, xr + 0.146, 16.387, rh - 0.99, rh + 0.4]),
              dict(name='Patio side beam', text='Patio side beam on the corner posts: 3-ply 2x12 (or 5-1/4" x 11-1/4" PSL), top at 9\'-0". Engineer to size.', box=[x0 - 0.25, 0.0, x0 + 0.25, 16.387, CEIL - 0.94, CEIL]),
              dict(name='Patio side beam', text='Patio side beam on the corner posts: 3-ply 2x12 (or 5-1/4" x 11-1/4" PSL), top at 9\'-0". Engineer to size.', box=[x1 - 0.25, 0.0, x1 + 0.25, 16.387, CEIL - 0.94, CEIL])]
    # porch: 2x8 rafters at 2:12 from a ledger on the front wall (Y 53.733) to the beam on the porch posts (Y 62.04)
    y0, y1, R = 53.733, 62.04, 7.25 / 12
    hi = CEIL + (y1 - y0) * 2 / 12
    for s in stations(31.0, 77.913):
        m = [(y0, hi + R / 2, y1 + 1.0, hi - (y1 + 1.0 - y0) * 2 / 12 + R / 2, R)]
        out.append(dict(axis='y', s=s, b=(y0, y1), kind='rafter', area='PO', members=[[round(v, 3) for v in mm] for mm in m]))
    beams += [dict(name='Porch beam', text='Porch beam on the five posts: 3-ply 2x12, top at 9\'-0". Rafters bear on it with hurricane ties.', box=[31.0, y1 - 0.25, 77.913, y1 + 0.25, CEIL - 0.94, CEIL]),
              dict(name='Porch ledger', text=f'Porch rafter ledger: 2x10 on the front wall, lagged to the wall framing through the sheathing, flashed; top {ft_in(hi + 0.3)} above the slab.', box=[31.0, y0 - 0.125, 77.913, y0, hi - 0.47, hi + 0.3])]
    return out, beams


def build():
    trusses = []
    for area in AREAS:
        first = area['s'][0] if area.get('girder') else None
        for i, s in enumerate(stations(*area['s'], first=first)):
            t = truss(area, s, girder=bool(area.get('girder')) and i == 0)
            if t: t['area'] = area['key']; trusses.append(t)
    raf, beams = rafters()
    # marks: identical profiles in an area share a mark
    marks, sig_mark, counts = {}, {}, {}
    for t in trusses:
        # a hip set (each step a little lower) is one mark per span
        sig = (t['area'], t['kind'], t['tall'], round(t['b'][1] - t['b'][0], 1), None if t['kind'] == 'hip' else round(t['peak'], 1))
        if sig not in sig_mark:
            n = sum(1 for k in sig_mark if k[0] == t['area'] and k[1] != 'girder') + 1
            sig_mark[sig] = 'G1' if t['kind'] == 'girder' else f"{t['area']}{n}"
        t['mark'] = sig_mark[sig]
        counts[t['mark']] = counts.get(t['mark'], 0) + 1
        marks.setdefault(t['mark'], t)
    for t in raf: t['mark'] = t['area']
    names = {a['key']: a['name'] for a in AREAS}
    kinds = {'common': 'common', 'scissor': 'scissor, 4:12 bottom chord (vault)', 'hip': 'hip set, stepped flat tops', 'girder': '2-ply girder, carries the master wing and garage trusses'}
    for t in trusses:
        span = t['b'][1] - t['b'][0]
        where = f"{'X' if t['axis'] == 'y' else 'Y'} {t['s']:.2f} from the datum"
        t['text'] = (f"Roof truss {t['mark']} ({names[t['area']]}): {kinds[t['kind']]}{', tall end at the patio' if t['tall'] else ''}, {where}. "
                     f"Span {ft_in(span)} bearing to bearing, 6:12, 12\" energy heel, 1'-6\" overhang, 24\" o.c.; peak {ft_in(CEIL + t['peak'])} above the slab. "
                     "Draft layout from A-2: the truss maker designs the real truss.")
    for t in raf:
        t['text'] = ('Patio rafter: 2x10 at 24" o.c., 6:12, from the side beam to the ridge beam; the vaulted patio ceiling is on the rafters (A-2).' if t['area'] == 'PR'
                     else 'Porch rafter: 2x8 at 24" o.c., 2:12 shed (A-2), ledger on the front wall to the beam on the posts, 1\' overhang.')
    def peak_range(mk):
        pk = sorted(CEIL + u['peak'] for u in trusses if u['mark'] == mk)
        return ft_in(pk[0]) if pk[-1] - pk[0] < 0.05 else f'{ft_in(pk[0])} to {ft_in(pk[-1])}'
    rows = []
    for mk, t in marks.items():
        span = t['b'][1] - t['b'][0]
        ss = [u['s'] for u in trusses if u['mark'] == mk]
        rows.append((None, [mk, names[t['area']], kinds[t['kind']] + (', tall end' if t['tall'] else ''), ft_in(span), '6:12' + (' / 4:12' if t['kind'] == 'scissor' else ''),
                            peak_range(mk), str(counts[mk]), f"{'X' if t['axis'] == 'y' else 'Y'} {min(ss):.1f} to {max(ss):.1f}"]))
    npr = sum(1 for t in raf if t['area'] == 'PR'); npo = len(raf) - npr
    rows.append((None, ['PR', 'Patio', '2x10 rafters on ridge and side beams', ft_in(64.21 - 43.79), '6:12', ft_in(CEIL + P * 10.21), str(2 * npr), 'Y 0.2 to 16.3, a pair per station']))
    rows.append((None, ['PO', 'Front porch', '2x8 rafters, ledger to beam', ft_in(62.04 - 53.733), '2:12', ft_in(CEIL + (62.04 - 53.733) / 6), str(npo), 'X 31.1 to 77.9']))
    summary = dict(trusses=len(trusses), rafters=2 * npr + npo)
    return dict(trusses=trusses + raf, beams=beams, rows=rows, summary=summary)


if __name__ == '__main__':
    b = build()
    print(b['summary'])
    for r in b['rows']: print(r[1])
