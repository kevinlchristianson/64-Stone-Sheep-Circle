"""P-1 Plumbing: fixture schedule, drain/vent stacks, under-slab drain tree and PEX supply.

Fixtures and drains are A-5's (plan/house.json). Everything else is a first
draft for the plumber: a slab-on-grade house (the garage and mechanical floor
drains point that way). One drain tree, sloped at the IPC minimums, collects
everything to a 4" building drain that leaves through the rear wall at 25,0
(Kevin's assumed connection, 2026-10-13); five fixture groups each vent to a
3" stack through the roof, with an island loop vent at the kitchen sink. Water:
one cold and hot PEX pair from the closet manifold to each fixture group, in
one piece under the slab, to a small group manifold, then short runs to the
fixtures. Drainage and supply fixture units from the IPC (Tables 709.1 and E103.3).
"""
from setlib import HOUSE, ROOMS, Sheet, ft_in, dist

DRAIN, VENT, COLD, HOT = '#3c3a36', '#4c8c4a', '#2c6aa0', '#c8382b'
FIX = {f['id']: f for f in HOUSE['fixtures']}

# kind -> (name, DFU, trap, WSFU cold, WSFU hot, supply size)
TABLE = {
    'wc': ('Water closet, 1.28 gpf tank', 3, '3"', 2.2, 0, '1/2"'),
    'lav': ('Lavatory', 1, '1-1/4"', 0.5, 0.5, '1/2"'),
    'tub': ('Bathtub', 2, '1-1/2"', 1.0, 1.0, '1/2"'),
    'shower': ('Shower', 2, '2"', 1.0, 1.0, '1/2"'),
    'sink': ('Kitchen sink', 2, '1-1/2"', 1.0, 1.0, '1/2"'),
    'dw': ('Dishwasher', 2, 'via sink tailpiece', 0, 1.4, '3/8" hot'),
    'washer': ('Clothes washer', 3, '2" standpipe', 1.0, 1.0, '1/2" box'),
    'drain': ('Floor / shower drain', 2, '2"', 0, 0, '—'),
}
PLUMBED = [f for f in HOUSE['fixtures'] if f['kind'] in TABLE]
MANIFOLD = (32.85, 46.4)
COLD_DROP, HOT_DROP = (32.7, 46.4), (33.0, 46.4)   # where the PEX leaves the manifold down into the slab: between R-1's feed pairs (x 32.4 and 33.25)
SERVICE = (31.2, 46.4)                             # the 1" service rises here, west of R-1's feed pairs
WATER_HEATER = (32.4, 51.0)
EXIT = (25.0, 0.0)    # where every drain leaves the house: the rear wall line, 25' from the datum (Kevin, 2026-10-13); sewer or septic beyond

STACKS = [
    dict(id='ST1', name='Master bath', at=(10.0, 16.8), fixtures=['MB-WC', 'MB-TUB', 'MB-LAV1', 'MB-LAV2', 'MB-SHR', 'MB-FD'], pipe='DM'),
    dict(id='ST2', name='Laundry and powder', at=(24.5, 25.0), fixtures=['LA-WASH', 'PR-WC', 'PR-LAV'], pipe='BD'),
    dict(id='ST3', name='Kitchen island (island vent)', at=(38.68, 28.6), fixtures=['K-SINK', 'K-DW'], pipe='DT'),
    dict(id='ST4', name='Bath 1', at=(79.7, 12.3), fixtures=['B1-WC', 'B1-LAV', 'B1-SHR', 'B1-FD'], pipe='DT'),
    dict(id='ST5', name='Bath 2', at=(78.6, 37.0), fixtures=['B2-WC', 'B2-LAV1', 'B2-LAV2', 'B2-TUB'], pipe='D2'),
]
# One drain tree to the exit. Each line flows from its first point to its last; the last point sits on the line it drains into.
# The 4" building drain runs straight out the rear at X 25; one 3" trunk at Y 26.8 picks up the kitchen and both east baths;
# the master bath comes in on its own 3" branch at Y 12; the two floor drains share a 2" line down X 25 from the garage.
TRUNK_Y = 26.8
PIPES = [
    dict(id='BD', name='4" building drain', size='4"', pts=[(25.0, TRUNK_Y), (25.0, 0.0), (25.0, -10.0)], into=None),
    dict(id='DT', name='East trunk: kitchen, bath 1, bath 2', size='3"', pts=[(80.5, 7.13), (80.5, TRUNK_Y), (25.0, TRUNK_Y)], into='BD'),
    dict(id='D2', name='Bath 2 branch', size='3"', pts=[(71.3, 38.2), (78.5, 38.2), (78.5, TRUNK_Y)], into='DT'),
    dict(id='DM', name='Master bath branch', size='3"', pts=[(7.9, 21.08), (7.9, 12.0), (25.0, 12.0)], into='BD'),
    dict(id='DF', name='Floor drain line, garage and mechanical', size='2"', pts=[(14.96, 52.14), (25.0, 52.14), (25.0, TRUNK_Y)], into='BD'),
]
PIPE = {d['id']: d for d in PIPES}
PIPE_OF = {'master_bath': 'DM', 'laundry': 'BD', 'powder': 'BD', 'kitchen': 'DT', 'bath1': 'DT', 'bath2': 'D2', 'mechanical': 'DF', 'garage': 'DF'}
SLOPE = {'4"': 0.125 / 12, '3"': 0.125 / 12, '2"': 0.25 / 12, '1-1/2"': 0.25 / 12}   # IPC 704.1: 1/8" per ft at 3" and up, 1/4" below
# Under the slab, top down, in feet from the slab top: 4" of concrete over R-1's 5" nub boards (the radiant loops ride on them,
# -0.33 to -0.75), R-1's 1" feed pairs right under the boards (-0.75 to -0.95), then P-1 in the base course below them in its own
# bands, so no pipe crosses another at the same depth: cold PEX, hot PEX under it, and the drains below both. The vent legs that
# run under the slab leave their fixture's drain at its own depth.
BOARD_BOTTOM = -0.75                  # R-1: radiant.BOARD_Z[0]
COLD_H, HOT_H = -1.02, -1.13          # PEX centre lines, about 12" and 13-1/2" down
DRAIN_TOP = -1.2                      # the highest any drain's crown (invert + outside diameter) comes, about 14-1/2" down
OD = {'4"': 4.5 / 12, '3"': 3.5 / 12, '2"': 2.375 / 12, '1-1/2"': 1.9 / 12}   # PVC DWV outside diameters
CLEANOUTS = [('CO1', (25.0, -1.5), '4" two-way cleanout outside the rear wall, at grade, where the building drain leaves'),
             ('CO2', (25.0, TRUNK_Y), '4" cleanout to the floor where the trunk, the floor drain line and the building drain meet'),
             ('CO3', (80.5, 7.13), '3" cleanout to the floor at the head of the east trunk (bath 1)')]
# Water: a 3/4" or 1/2" cold and hot pair from the closet manifold to each fixture group, in one piece under the slab (no joints
# under the slab), to a small manifold in that group's vanity or wet wall, then short 1/2" lines to the fixtures.
GROUPS = [
    dict(id='PM-1', name='Master bath', at=(15.08, 9.63), where='in the double vanity base', fixtures=['MB-WC', 'MB-TUB', 'MB-LAV1', 'MB-LAV2', 'MB-SHR'], cold='3/4"', hot='3/4"'),
    dict(id='PM-2', name='Laundry and powder', at=(24.81, 24.2), where='in the laundry / powder wet wall, behind an access panel on the laundry side', fixtures=['LA-WASH', 'PR-WC', 'PR-LAV'], cold='3/4"', hot='1/2"'),
    dict(id='K-SINK', name='Kitchen island', at=(38.68, 27.6), where='straight to the sink stops; the dishwasher tees off the hot stop under the sink', fixtures=['K-SINK', 'K-DW'], cold='1/2"', hot='1/2"', direct=True),
    dict(id='PM-3', name='Bath 1', at=(77.73, 11.0), where='in the bath 1 / bedroom 1 wall, behind an access panel in the bedroom 1 closet side', fixtures=['B1-LAV', 'B1-WC', 'B1-SHR'], cold='3/4"', hot='1/2"'),
    dict(id='PM-4', name='Bath 2', at=(72.87, 38.98), where='in the double vanity base', fixtures=['B2-LAV1', 'B2-LAV2', 'B2-WC', 'B2-TUB'], cold='3/4"', hot='1/2"'),
]
GROUP_OF = {fid: g for g in GROUPS for fid in g['fixtures']}
GAL_PER_FT = {'1/2"': 0.0092, '3/4"': 0.0184}   # PEX inside volume
HOSE = [dict(id='HB1', at=(36.0, 53.9), name='Hose bibb, front porch (frost-free)'),
        dict(id='HB2', at=(46.0, 16.6), name='Hose bibb, rear patio (frost-free)'),
        dict(id='HB3', at=(0.5, 44.0), name='Hose bibb, garage door wall (frost-free)')]


def plen(pts): return sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def manhattan(a, b, first='x'):
    return [a, (b[0], a[1]), b] if first == 'x' else [a, (a[0], b[1]), b]


# ---------------------------------------------------------------- vents and the 3D model (Zero Rd's buildPlumbing, for a slab)
CEIL = HOUSE['meta']['ceiling_ft']
VENT_H = CEIL + 0.75                           # vent runs in the attic, over the ceiling
# house and garage outline (outside of the walls), for how high the roof is over a point: 6:12 from a 12" heel, 1'-6" eaves
OUTLINE = [(16.0, 0.0), (31.0, 0.0), (31.0, 5.08), (44.167, 5.08), (44.167, 16.387), (64.0, 16.387), (64.0, 5.08), (83.44, 5.08), (83.44, 45.733), (77.913, 45.733),
           (77.913, 53.733), (31.0, 53.733), (31.0, 70.093), (14.96, 70.093), (14.96, 67.593), (0.0, 67.593), (0.0, 36.673), (5.373, 36.673), (5.373, 5.08), (16.0, 5.08)]
SIZE_R = {'4"': 0.17, '3"': 0.13, '2"': 0.09, '1-1/2"': 0.07}


def _seg_dist(p, a, b):
    ax, ay, bx, by = *a, *b
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    t = 0 if not L2 else max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / L2))
    return dist(p, (ax + t * (bx - ax), ay + t * (by - ay)))


def roof_over(p):
    d = min(_seg_dist(p, OUTLINE[i - 1], OUTLINE[i]) for i in range(len(OUTLINE)))
    return CEIL + 1.0 + 0.5 * (d + 1.5)


def wall_point(p):
    """The point in the nearest wall (on its centre line) behind a fixture: where its vent rises."""
    best = None
    for w in HOUSE['walls']:
        cx, cy = min(max(p[0], w['x0']), w['x1']), min(max(p[1], w['y0']), w['y1'])
        q = (cx, (w['y0'] + w['y1']) / 2) if w['x1'] - w['x0'] >= w['y1'] - w['y0'] else ((w['x0'] + w['x1']) / 2, cy)
        d = dist(p, (cx, cy))
        if best is None or d < best[0]: best = (d, (round(q[0], 2), round(q[1], 2)), w['kind'])
    return best


def _seg_of(pts, q, tol=0.05):
    for i in range(len(pts) - 1):
        if _seg_dist(q, pts[i], pts[i + 1]) < tol: return i
    raise ValueError(f'{q} is not on {pts}')


def nearest_on(pts, p):
    """The closest point to p on an axis-aligned polyline, and whether that segment runs along X."""
    best = None
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        q = (min(max(p[0], min(ax, bx)), max(ax, bx)), min(max(p[1], min(ay, by)), max(ay, by)))
        d = dist(p, q)
        if best is None or d < best[0]: best = (d, q, abs(by - ay) < 1e-6)
    return best[1], best[2]


def drain_net():
    """Lay out the drain tree and slope it. Every line falls toward the exit at IPC minimum slope; the inverts are worked back
    from the exit, then the whole tree is set so the highest crown sits at DRAIN_TOP, under the PEX. Returns the lines with
    an invert per point, each fixture's arm, each stack's base leg, and the invert where the drain leaves the house."""
    Z = {}
    def z_at(pid, q):
        pts, zs, sl = PIPE[pid]['pts'], Z[pid], SLOPE[PIPE[pid]['size']]
        i = _seg_of(pts, q)
        return zs[i + 1] + sl * dist(q, pts[i + 1])
    def slope_back(pts, z_end, size):
        zs = [0.0] * len(pts); zs[-1] = z_end
        for i in range(len(pts) - 2, -1, -1): zs[i] = zs[i + 1] + SLOPE[size] * dist(pts[i], pts[i + 1])
        return zs
    for d in PIPES:
        Z[d['id']] = slope_back(d['pts'], z_at(d['into'], d['pts'][-1]) if d['into'] else 0.0, d['size'])
    arms, legs = {}, {}
    showers = {f['room'] for f in PLUMBED if f['kind'] == 'shower'}
    for f in PLUMBED:
        if f['kind'] == 'dw' or f['kind'] == 'shower' and f['room'] in showers and any(g['kind'] == 'drain' and g['room'] == f['room'] for g in PLUMBED): continue
        pid = PIPE_OF[f['room']]
        q, along_x = nearest_on(PIPE[pid]['pts'], f['at'])
        arm = [p for i, p in enumerate(manhattan(tuple(f['at']), q, 'x' if along_x else 'y')) if i == 0 or dist(p, manhattan(tuple(f['at']), q, 'x' if along_x else 'y')[i - 1]) > 1e-6]
        size = arm_size(f)
        arms[f['id']] = dict(pts=arm, size=size, pipe=pid, z=slope_back(arm, z_at(pid, q), size) if len(arm) > 1 else [z_at(pid, q)])
    for st in STACKS:
        if st['id'] == ISLAND: continue
        q, along_x = nearest_on(PIPE[st['pipe']]['pts'], st['at'])
        leg = [p for i, p in enumerate(manhattan(st['at'], q, 'x' if along_x else 'y')) if i == 0 or dist(p, manhattan(st['at'], q, 'x' if along_x else 'y')[i - 1]) > 1e-6]
        legs[st['id']] = dict(pts=leg, z=slope_back(leg, z_at(st['pipe'], q), '3"') if len(leg) > 1 else [z_at(st['pipe'], q)])
    top = max([max(Z[d['id']]) + OD[d['size']] for d in PIPES] + [max(a['z']) + OD[a['size']] for a in arms.values()] + [max(l['z']) + OD['3"'] for l in legs.values()])
    off = DRAIN_TOP - top
    for k in Z: Z[k] = [z + off for z in Z[k]]
    for a in list(arms.values()) + list(legs.values()): a['z'] = [z + off for z in a['z']]
    return dict(pipes={d['id']: dict(d, z=Z[d['id']]) for d in PIPES}, arms=arms, legs=legs, exit_invert=z_at('BD', EXIT))


def dfu_into(pid):
    """Drainage fixture units a line carries: its own fixtures and every line upstream of it."""
    own = sum(TABLE[f['kind']][1] for f in PLUMBED if PIPE_OF.get(f['room']) == pid)
    return own + sum(dfu_into(d['id']) for d in PIPES if d['into'] == pid)


def _inside(poly, p):
    c = False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[i - 1]
        if (y0 > p[1]) != (y1 > p[1]) and p[0] < (x1 - x0) * (p[1] - y0) / (y1 - y0) + x0: c = not c
    return c


def _seg_seg2(a, b, c, d):
    """Plan distance between segments ab and cd."""
    def cross(o, p, q): return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    if (cross(a, b, c) > 0) != (cross(a, b, d) > 0) and (cross(c, d, a) > 0) != (cross(c, d, b) > 0): return 0.0
    return min(_seg_dist(a, c, d), _seg_dist(b, c, d), _seg_dist(c, a, b), _seg_dist(d, a, b))


def _crosses(a, b, c, d, m=0.05):
    """Do two axis-aligned segments, one along X and one along Y, cross through each other's middles (not a T or a corner)?"""
    if (abs(a[1] - b[1]) < 1e-6) == (abs(c[1] - d[1]) < 1e-6): return False
    (h0, h1), (v0, v1) = ((a, b), (c, d)) if abs(a[1] - b[1]) < 1e-6 else ((c, d), (a, b))
    x, y = v0[0], h0[1]
    return min(h0[0], h1[0]) + m < x < max(h0[0], h1[0]) - m and min(v0[1], v1[1]) + m < y < max(v0[1], v1[1]) - m


class Router:
    """Lays the PEX runs one at a time, each in its own band under the slab (cold, or hot below it), on the shortest route of two
    or three legs that stays under the heated house where it can, clears every riser that comes up through the bands (drain risers,
    stacks, cleanouts, vents, the service, the PEX risers themselves) and crosses no run already laid in the same band. Runs that
    leave the same manifold go out together as a bundle."""
    GAP = 0.03

    def __init__(self, posts):
        self.posts = posts                       # (x, y, r)
        self.laid = {'cold': [], 'hot': []}      # (a, b, r, origin, group)

    def clashes(self, pts, band, r, origin, group):
        n = 0
        ends = (pts[0], pts[-1])
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            for x, y, pr in self.posts:
                if min(dist((x, y), e) for e in ends) < 0.45: continue
                if _seg_dist((x, y), a, b) < r + pr + self.GAP: n += 1
            for c, d, r2, o2, g2 in self.laid[band]:
                if o2 == origin or o2 == group or g2 == origin:   # same bundle: may run alongside and branch off, never cross
                    if _crosses(a, b, c, d): n += 1
                elif _seg_seg2(a, b, c, d) < r + r2 + self.GAP: n += 1
        return n

    _cache = {}

    @classmethod
    def _out(cls, p):
        """1 outside the heated house, 0.5 inside but within 6" of its outside wall line (keep inside the footing), else 0."""
        k = (round(p[0], 2), round(p[1], 2))
        if k not in cls._cache:
            env = HOUSE['envelope']
            cls._cache[k] = 1.0 if not _inside(env, p) else 0.5 if min(_seg_dist(p, env[i - 1], env[i]) for i in range(len(env))) < 0.5 else 0.0
        return cls._cache[k]

    @classmethod
    def outside(cls, pts):
        n = 0
        for i in range(len(pts) - 1):
            L = dist(pts[i], pts[i + 1]); k = max(1, int(L))
            n += sum(cls._out((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * j / k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * j / k)) for j in range(k + 1))
        return n

    def route(self, a, b, band, r, origin, group=None):
        a, b = tuple(a), tuple(b)
        cands = [manhattan(a, b, 'y'), manhattan(a, b, 'x')]
        for ax in (0, 1):
            lo, hi = min(a[ax], b[ax]) - 2.0, max(a[ax], b[ax]) + 2.0
            for k in range(int(lo * 4), int(hi * 4) + 1):
                m = k / 4
                cands.append([a, (m, a[1]), (m, b[1]), b] if ax == 0 else [a, (a[0], m), (b[0], m), b])
        best = None
        for c in cands:
            c = [p for i, p in enumerate(c) if i == 0 or dist(p, c[i - 1]) > 1e-6]
            score = (self.clashes(c, band, r, origin, group), self.outside(c), plen(c) + 0.5 * (len(c) - 2))
            if best is None or score < best[0]: best = (score, c)
        pts = best[1]
        for i in range(len(pts) - 1): self.laid[band].append((pts[i], pts[i + 1], r, origin, group))
        return pts, best[0][0]


PR = {'1"': 0.09, '3/4"': 0.05, '1/2"': 0.035}   # PEX as drawn in 3D (a little fatter than real, so it reads)
STUB_TOP = {'wc': 0.7, 'tub': 2.4, 'shower': 4.0, 'washer': 3.5}


def vent_low(v, NET):
    """Where a vent that runs under the slab leaves its fixture's drain: at the drain's centre line (a shower's at its floor drain)."""
    f = v['fixture']
    a = NET['arms'].get(f['id']) or next(NET['arms'][g['id']] for g in PLUMBED if g['kind'] == 'drain' and g['room'] == f['room'])
    return a['z'][0] + OD[a['size']] / 2


def supply_net(NET, VENTS):
    """Cold and hot runs: closet manifold to each group manifold, group manifold to each fixture, and the hose bibbs; hot wait at
    the farthest fixture. Everything that comes up through the PEX bands is a post the runs keep clear of."""
    posts = [(*SERVICE, PR['1"']), (*COLD_DROP, PR['3/4"']), (*HOT_DROP, PR['3/4"'])]
    for fid, a in NET['arms'].items(): posts.append((*FIX[fid]['at'], 0.15 if FIX[fid]['kind'] == 'wc' else SIZE_R[a['size']]))
    posts += [(*s['at'], 0.13) for s in STACKS if s['id'] != ISLAND]
    posts += [(*at, SIZE_R['4"' if id == 'CO2' else '3"']) for id, at, _ in CLEANOUTS if id != 'CO1']
    for v in VENTS:
        if v.get('under'): posts.append((*v['wall'], SIZE_R[v['size']] * 0.8))
        if v.get('loop'): x, y = v['fixture']['at']; posts += [(x + 0.3, y, 0.072), (x + 0.6, y + 0.3, 0.072)]
    for g in GROUPS:
        gx, gy = g['at']; posts += [(gx, gy, PR[g['cold']]), (gx + 0.3, gy + 0.3, PR[g['hot']])]
        for fid in g['fixtures']:
            x, y = FIX[fid]['at']; posts += [(x, y, PR['1/2"']), (x + 0.25, y + 0.25, PR['1/2"'])]
    posts += [(*h['at'], PR['3/4"']) for h in HOSE]
    R = Router(posts)
    out, bad = [dict(g, stubs={}, hot_stubs={}) for g in GROUPS], 0
    for g in out:   # the short runs first, so the long feeds go around the other groups' fixtures
        if g.get('direct'): continue
        gx, gy = g['at']
        for fid in g['fixtures']:
            k = FIX[fid]['kind']
            if k == 'dw': continue
            x, y = FIX[fid]['at']
            if TABLE[k][3]: g['stubs'][fid], n = R.route(g['at'], (x, y), 'cold', PR['1/2"'], g['id']); bad += n
            if TABLE[k][4]: g['hot_stubs'][fid], n = R.route((gx + 0.25, gy + 0.25), (x + 0.25, y + 0.25), 'hot', PR['1/2"'], g['id']); bad += n
    for g in out:
        gx, gy = g['at']
        g['cold_run'], n1 = R.route(COLD_DROP, g['at'], 'cold', PR[g['cold']], 'MAN', g['id'])
        g['hot_run'], n2 = R.route(HOT_DROP, (gx + 0.3, gy + 0.3), 'hot', PR[g['hot']], 'MAN', g['id'])
        bad += n1 + n2
    for h in HOSE:
        h['run'], n = R.route(COLD_DROP, h['at'], 'cold', PR['3/4"'], 'MAN', h['id']); bad += n
    for g in out:
        far = max([plen(r) for r in g['hot_stubs'].values()] or [0])
        g['hot_gal'] = plen(g['hot_run']) * GAL_PER_FT[g['hot']] + far * GAL_PER_FT['1/2"']
        g['wait_s'] = g['hot_gal'] / 1.5 * 60
    return out, bad


def arm_size(f):
    return '2"' if f['kind'] in ('shower', 'washer', 'drain') else '3"' if f['kind'] == 'wc' else '1-1/2"'


ISLAND = 'ST3'
VENT_AT = {'B1-SHR': (80.75, 15.98)}   # moved along its wall to come up between R-1's leaders under it (ST4 is set between R-1's tubes too)


def vents():
    """Every trap gets a vent. Wall fixtures: up inside the wall behind the fixture, then across the attic to their group's
    stack. Shower floor drains share the shower's vent; the dishwasher drains through the sink. The island sink gets a
    loop vent (up inside the island, back down, under the slab to the laundry wall and up to ST2's vent in the attic).
    The garage and mechanical floor drains have no stack near them: each gets its own 2" vent through the roof."""
    stack_of = {fid: s for s in STACKS for fid in s['fixtures']}
    showers = {f['room'] for f in PLUMBED if f['kind'] == 'shower'}
    st = {s['id']: s for s in STACKS}
    out = []
    for f in PLUMBED:
        if f['kind'] == 'dw' or (f['kind'] == 'drain' and f['room'] in showers): continue
        s = stack_of.get(f['id'])
        d, wp, kind = wall_point(f['at'])
        wp = VENT_AT.get(f['id'], wp)
        v = dict(ref=f['id'], fixture=f, size='2"' if f['kind'] in ('wc', 'drain', 'washer') else '1-1/2"', wall=wp, ext=kind == 'E')
        if s and s['id'] == ISLAND:
            v.update(loop=True, under=manhattan(f['at'], wp, 'y'), attic=manhattan(wp, st['ST2']['at'], 'x'), to='ST2', size='2"')
        elif s:
            v.update(under=manhattan(f['at'], wp, 'y') if d > 1.6 else None, attic=manhattan(wp, s['at'], 'x'), to=s['id'])
        else:
            v.update(under=manhattan(f['at'], wp, 'y') if d > 1.6 else None, attic=None, to=None)
        out.append(v)
    return out


def build():
    sh = Sheet('P-1', 'Plumbing', 'Fixtures from A-5; one drain tree out the rear wall at 25,0, and group PEX feeds. A first draft for the plumber (slab on grade).')
    sh.base()
    picks, fix_rows = {}, []
    stack_of = {fid: s for s in STACKS for fid in s['fixtures']}
    NET, VENTS = drain_net(), vents()
    SUP, bad = supply_net(NET, VENTS)
    assert not bad, f'{bad} PEX runs could not clear the risers or each other'
    dfu_total = sum(TABLE[f['kind']][1] for f in PLUMBED)
    wsfu_c = sum(TABLE[f['kind']][3] for f in PLUMBED) + 2.5 * len(HOSE)
    wsfu_h = sum(TABLE[f['kind']][4] for f in PLUMBED)
    drain_lf = {'4"': 0, '3"': 0, '2"': 0, '1-1/2"': 0}
    depth = lambda z: ft_in(-z)
    top_inv = max([max(d['z']) for d in NET['pipes'].values()] + [max(a['z']) for a in NET['arms'].values()] + [max(l['z']) for l in NET['legs'].values()])
    # supply first, under everything: group runs heavier, short lines to the fixtures light
    pex_lf, hot_lf = {'3/4"': 0, '1/2"': 0}, 0.0
    for g in SUP:
        sh.path(g['cold_run'], COLD, 1.4 if g['cold'] == '3/4"' else 1.0, extra=' opacity="0.7"'); pex_lf[g['cold']] += plen(g['cold_run'])
        sh.path(g['hot_run'], HOT, 1.4 if g['hot'] == '3/4"' else 1.0, extra=' opacity="0.7"'); pex_lf[g['hot']] += plen(g['hot_run']); hot_lf += plen(g['hot_run'])
        for r in g['stubs'].values(): sh.path(r, COLD, 0.6, extra=' opacity="0.55"'); pex_lf['1/2"'] += plen(r)
        for r in g['hot_stubs'].values(): sh.path(r, HOT, 0.6, extra=' opacity="0.55"'); pex_lf['1/2"'] += plen(r); hot_lf += plen(r)
    for h in HOSE:
        sh.path(h['run'], COLD, 1.4, extra=' opacity="0.7"'); pex_lf['3/4"'] += plen(h['run'])
    # drains: lines (clickable), then fixture arms and stack legs
    for d in NET['pipes'].values():
        title = f"{d['id']} · {d['name']}, {d['size']}, {dfu_into(d['id'])} DFU"
        sh.open_group(d['id'], title)
        sh.path(d['pts'] if d['id'] != 'BD' else d['pts'][:-1] + [(25.0, -1.8)], DRAIN, {'4"': 3.4, '3"': 2.4, '2"': 1.8}[d['size']], '6,3' if d['id'] == 'DF' else None)
        sh.close_group()
        drain_lf[d['size']] += plen(d['pts'])
        into = 'leaves the house at 25,0 for the sewer or septic' if not d['into'] else f"drains into {d['into']} ({PIPE[d['into']]['name']})"
        picks[d['id']] = dict(tag=d['id'], sub=d['name'], fields=[('Pipe', f"{d['size']} PVC DWV under the slab, {plen(d['pts']):.0f} ft"), ('Load', f"{dfu_into(d['id'])} DFU"),
                                                                ('Slope', f"{'1/8' if d['size'] in ('4\"', '3\"') else '1/4'}\" per ft toward the exit"),
                                                                ('Invert', f"{depth(d['z'][0])} below the floor at its head, {depth(d['z'][-1])} where it {'leaves' if not d['into'] else 'joins ' + d['into']}"), ('Runs to', into)])
    for fid, a in NET['arms'].items():
        if len(a['pts']) > 1: sh.path(a['pts'], DRAIN, 1.3); drain_lf[a['size']] += plen(a['pts'])
    for sid, l in NET['legs'].items():
        if len(l['pts']) > 1: sh.path(l['pts'], DRAIN, 1.6); drain_lf['3"'] += plen(l['pts'])
    # vents: under-slab legs dashed, the riser in the wall a dot, attic runs to the stack thin green
    for v in VENTS:
        if v.get('under'): sh.path(v['under'], VENT, 1.0, '4,2')
        if v.get('attic'): sh.path(v['attic'], VENT, 1.0, extra=' opacity="0.8"')
        sh.circle(*v['wall'], 0.22, VENT, VENT, 0)
    for s in STACKS:
        x, y = s['at']
        dfu = sum(TABLE[FIX[fid]['kind']][1] for fid in s['fixtures'])
        sh.open_group(s['id'], f"{s['id']} · {s['name']} stack, {dfu} DFU", hit=(x, y, 0.9))
        sh.circle(x, y, 0.55, '#fff', VENT, 2.0); sh.circle(x, y, 0.22, VENT, VENT, 0)
        sh.close_group()
        sh.text(x + 1.4, y - 0.9, s['id'], 7, VENT, '700')
        vent = '3" vent through the roof' if s['id'] != ISLAND else 'island loop vent or AAV (where allowed), 2"'
        picks[s['id']] = dict(tag=s['id'], sub=s['name'], fields=[('Fixtures', ', '.join(f"{FIX[fid]['name']} ({fid})" for fid in s['fixtures'])),
                                                               ('Drainage', f"{dfu} DFU into {s['pipe']} ({PIPE[s['pipe']]['name']})"), ('Vent', vent),
                                                               ('Base', 'the island sink drains straight down into the trunk' if s['id'] == ISLAND else f"3\" stack base {plen(NET['legs'][s['id']]['pts']):.1f} ft from {s['pipe']}, invert {depth(NET['legs'][s['id']]['z'][0])} below the floor")])
    # group manifolds
    for g in SUP:
        x, y = g['at']
        far = max(g['hot_stubs'].items(), key=lambda kv: plen(kv[1]))[0] if g['hot_stubs'] else g['fixtures'][0]
        fields = [('Feeds', ', '.join(f"{FIX[fid]['name']} ({fid})" for fid in g['fixtures'])), ('Where', g['where']),
                  ('Cold', f"{g['cold']} PEX from MAN, {plen(g['cold_run']):.0f} ft in one piece under the slab"), ('Hot', f"{g['hot']} PEX from MAN, {plen(g['hot_run']):.0f} ft in one piece under the slab"),
                  ('Hot wait', f"about {g['wait_s']:.0f} s at 1.5 gpm to the farthest hot fixture ({far}), {g['hot_gal']:.2f} gal in the line")]
        if g.get('direct'):
            picks.setdefault(g['id'], dict(tag=g['id'], sub=g['name'], fields=[]))
            continue
        sh.open_group(g['id'], f"{g['id']} · {g['name']} manifold", hit=(x, y, 0.9))
        sh.rect(x - 0.45, y - 0.45, x + 0.45, y + 0.45, '#fff', COLD, 1.4); sh.line(x - 0.45, y + 0.45, x + 0.45, y - 0.45, HOT, 1.2)
        sh.close_group()
        sh.text(x + (1.5 if x < 70 else -1.5), y - 1.0, g['id'], 6, COLD, '700', anchor='start' if x < 70 else 'end')
        picks[g['id']] = dict(tag=g['id'], sub=f"{g['name']} manifold", fields=[('Item', '1/2" PEX manifold with stops, cold and hot; 1/2" lines to each fixture')] + fields)
    group_fields = {g['id']: g for g in SUP}
    # fixtures as picks
    for f in PLUMBED:
        name, dfu, trap, wc, wh, sup = TABLE[f['kind']]
        s, g, a = stack_of.get(f['id']), GROUP_OF.get(f['id']), NET['arms'].get(f['id'])
        x, y = f['at']
        sh.open_group(f['id'], f"{f['id']} · {f['name']}", hit=(x, y, 0.9))
        sh.circle(x, y, 0.35, DRAIN if f['kind'] == 'drain' else '#fff', DRAIN, 1.0)
        sh.close_group()
        rm = ROOMS[f['room']]['name']
        if g and g.get('direct'): supply = f"1/2\" cold and hot straight from MAN ({plen(group_fields[g['id']]['cold_run']):.0f} ft)" if f['kind'] == 'sink' else '3/8" hot off the sink hot stop'
        elif g: supply = f"{sup} PEX from {g['id']} ({g['name']} manifold), {plen(group_fields[g['id']]['stubs'][f['id']]):.0f} ft" + (' (cold and hot)' if wc and wh else ' (hot)' if wh else ' (cold)' if wc else '')
        else: supply = '—'
        drain = (f"{a['size']} arm, {plen(a['pts']):.1f} ft to {a['pipe']}" if len(a['pts']) > 1 else f"straight into {a['pipe']}") + f", invert {depth(a['z'][0])} below the floor" if a else \
                ('through the floor drain beside it' if f['kind'] == 'shower' else 'through the sink tailpiece' if f['kind'] == 'dw' else '—')
        fields = [('Fixture', f['name']), ('Room', rm), ('Trap / drain', trap), ('DFU', str(dfu)), ('Drain', drain), ('Supply', supply),
                  ('Stack', f"{s['id']} {s['name']}" if s else 'own vent (no stack nearby)')]
        v = next((v for v in VENTS if v['ref'] == f['id']), None)
        if v: fields.append(('Vent', f"{v['size']} up the {'exterior' if v['ext'] else 'interior'} wall behind it" + (f", across the attic to {v['to']}" if v['to'] else ', through the roof on its own') + (' (loop vent in the island first, then under the slab to the wall)' if v.get('loop') else ' (under the slab to the wall first)' if v.get('under') else '')))
        if f['id'] == 'GA-FD': fields.append(('Code', 'A garage floor drain to the sanitary sewer needs an oil/sand interceptor in most jurisdictions; or drain to daylight'))
        if f['id'] == 'PR-LAV': fields.append(('Note', 'Not drawn on A-5; assumed so the powder room has a sink'))
        picks[f['id']] = dict(tag=f['id'], sub=rm, fields=fields)
        fix_rows.append((f['id'], [f['id'], f['name'], rm, trap, str(dfu), sup if f['kind'] != 'drain' else '—', (g['id'] if g and not g.get('direct') else 'MAN' if g else '—'), s['id'] if s else 'own vent']))
    picks['K-SINK']['fields'].insert(0, ('Group', 'Kitchen island: no group manifold, the pair runs straight from MAN'))
    for h in HOSE:
        x, y = h['at']
        sh.open_group(h['id'], h['name'], hit=(x, y, 0.8)); sh.rect(x - 0.3, y - 0.3, x + 0.3, y + 0.3, COLD, COLD, 0); sh.close_group()
        picks[h['id']] = dict(tag=h['id'], sub='Hose bibb', fields=[('Fixture', h['name']), ('Supply', f"3/4\" PEX from MAN, {plen(h['run']):.0f} ft, frost-free sillcock with vacuum breaker")])
        fix_rows.append((h['id'], [h['id'], h['name'], 'Outside', '—', '—', '3/4"', 'MAN', '—']))
    # manifold, water heater, cleanouts
    for id, at, name, color in [('MAN', MANIFOLD, 'Main manifold and shutoff (water service enters here)', COLD), ('WH', WATER_HEATER, 'Water heater, 50 gal (heat-pump or gas, confirm)', HOT)]:
        x, y = at
        sh.open_group(id, name, hit=(x, y, 0.9)); sh.rect(x - 0.6, y - 0.6, x + 0.6, y + 0.6, '#fff', color, 1.6); sh.text(x, y, id, 5.5, color, '700'); sh.close_group()
    picks['MAN'] = dict(tag='MAN', sub='Mechanical closet', fields=[('Item', f"Main manifold with the main shutoff (and a PRV if street pressure is over 80 psi): {len(SUP) + len(HOSE)} cold and {len(SUP)} hot outlets, one pair to each fixture group, plus the hose bibbs"),
                                                                  ('Service', '1" water service, entry location not on the site plan'), ('Load', f'{wsfu_c + wsfu_h:.1f} WSFU total')])
    picks['WH'] = dict(tag='WH', sub='Mechanical closet', fields=[('Item', '50 gal water heater on a drain pan to the floor drain; expansion tank; T&P to the floor drain'),
                                                               ('Sizing', 'two tubs and two showers: 50 gal heat-pump (≥ 65 gal first-hour) or gas; a heat-pump unit needs ~700 cu ft of air or ducting, which this 3\' x 8\' closet lacks — see open items')])
    for id, at, text in CLEANOUTS:
        x, y = at
        sh.open_group(id, text, hit=(x, y, 0.7)); sh.circle(x, y, 0.3, '#fff', DRAIN, 1.4); sh.close_group()
        sh.text(x + 0.9, y + 0.9, id, 5.5, DRAIN, '700', anchor='start') if id != 'CO1' else sh.text(x - 0.8, y, id, 5.5, DRAIN, '700', anchor='end')
        picks[id] = dict(tag=id, sub='Cleanout', fields=[('Item', text)] + ([('Exit invert', f"{depth(NET['exit_invert'])} below the finished floor at the rear wall (25,0)")] if id == 'CO1' else []))
    sh.text(26.6, -0.75, f'4" drain out at 25,0, invert {depth(NET["exit_invert"])}, to sewer / septic', 5.5, DRAIN, '600', anchor='start')

    hot_far = max(SUP, key=lambda g: g['wait_s'])
    supply_gpm = round(0.5 * (wsfu_c + wsfu_h) ** 0.75 + 4, 1)  # rough Hunter curve fit for small counts
    notes = [
        'Slab on grade assumed (A-5 shows floor drains in the garage and mechanical closet). All drains and supply runs are under the slab or in walls; no water lines in the attic.',
        f'One drain tree, every line falling to where the building drain leaves the house at 25,0 (the rear wall line) at an invert of {depth(NET["exit_invert"])} below the finished floor: a 4" building drain straight out the rear at X 25, '
        f'a 3" east trunk at Y {TRUNK_Y:g} for the kitchen and both east baths, a 3" master bath branch at Y 12, and a 2" line from the garage and mechanical floor drains. {dfu_total} DFU in all.',
        'Slopes are the IPC minimums (1/8" per ft at 3" and 4", 1/4" per ft below 3"), worked back from the exit; the shallowest invert is ' + depth(top_inv) + ' under the slab.',
        f'Under the slab, top down: 4" of concrete; R-1\'s 5" nub boards with the radiant loops on them ({depth(BOARD_BOTTOM)} to their underside); R-1\'s 1" feed pairs right under the boards; then P-1 in the base course, each in its own band so nothing crosses at the same depth: '
        f'cold PEX about {depth(COLD_H)} down, hot PEX about {depth(HOT_H)} down, and every drain below both (crowns no higher than {depth(DRAIN_TOP)}). Vent legs under the slab leave their drain at its own depth. '
        'Rough in, test and backfill the plumbing before the vapor barrier and boards go down; sleeve each line where it comes up through the boards and slab.',
        f'Supply: 1" service to a main manifold in the mechanical closet, then one cold and hot pair to each fixture group, in one piece under the slab (no fittings under the slab), to a small manifold in the vanity or wet wall; '
        f'short 1/2" lines from there to each fixture. {pex_lf["3/4\""] + pex_lf["1/2\""]:.0f} ft of PEX in all. {wsfu_c:.1f} cold + {wsfu_h:.1f} hot WSFU. Hot runs under the slab get R-3 closed-cell insulation (IECC R403.5.3), since they sit below the radiant boards. Pressure-balanced or thermostatic valves at the tubs and showers.',
        f"Hot water takes longest at {hot_far['name'].lower()} (about {hot_far['wait_s']:.0f} s at a lavatory); see open items for a recirculation pump.",
        'Every trap is vented: up the wall behind the fixture and across the attic to its group\'s 3" stack, which goes through the roof. Wet walls framed 2x6 (see S-1). ADA toilets as drawn: 17-19" bowl height, grab-bar blocking.',
        'Water heater in the mechanical closet with a pan and the T&P and pan drain to the closet floor drain.',
    ]
    open_items = [
        f'Confirm the drain leaves at 25,0 (assumed): city sewer or septic, and the invert there. The house needs about {depth(NET["exit_invert"])} of cover at the wall plus the fall to the main or tank.',
        'Water source (city or well) and where it enters; the main manifold is drawn in the mechanical closet.',
        f"A demand recirculation pump (button or motion sensor at each bath) on the hot side would cut the wait at the far baths to a few seconds; it needs a 1/2\" return or the cold line as the return.",
        'Water heater fuel and type. A heat-pump water heater needs about 700 cu ft of air or a ducted kit; the 3\' x 8\' mechanical closet is too small without one. A gas unit needs venting and combustion air.',
        'Powder room sink is not drawn on A-5 (one is shown here, assumed).',
        'Garage floor drain: sanitary with an interceptor, or to daylight (lot grading).',
        'Kitchen island vent method (loop vent vs. AAV) depends on the local code.',
        'Fixture models: A-5 tags the drains K-9135 and K-9136; tub, toilet, faucet and valve models still to pick.',
    ]
    sh.title_block(['Drains black, heavier for bigger pipe (4" building drain out the rear at 25,0); floor-drain line dashed; stacks green.', 'Vents green: a dot where each rises in the wall, thin line across the attic to its stack, dashed where it runs under the slab.',
                    'PEX: cold blue, hot red; heavy lines are the group feeds from MAN, light lines the short runs from each group manifold (PM) to its fixtures.', 'Routing is schematic: the plumber lays out the final runs.'])
    tables = [
        dict(key='fixtures', title='Fixture schedule', cols=['Tag', 'Fixture', 'Room', 'Trap / drain', 'DFU', 'Supply', 'Fed from', 'Stack'], rows=fix_rows),
        dict(key='drains', title='Drain lines', lede=f'Every line falls to the exit at 25,0. Inverts are below the finished floor.', cols=['Line', 'What it carries', 'Size', 'Length', 'DFU', 'Invert at the head', 'Invert at the end'],
             rows=[(d['id'], [d['id'], d['name'], d['size'], f"{plen(d['pts']):.0f} ft", str(dfu_into(d['id'])), depth(d['z'][0]), depth(d['z'][-1])]) for d in NET['pipes'].values()]),
        dict(key='supply', title='Water supply groups', lede='Each pair runs in one piece under the slab from the main manifold (MAN) in the mechanical closet.', cols=['Group', 'Fixtures', 'Cold', 'Hot', 'Feed length', 'Hot wait'],
             rows=[(g['id'], [g['id'], g['name'], g['cold'], g['hot'], f"{plen(g['cold_run']):.0f} ft", f"~{g['wait_s']:.0f} s"]) for g in SUP]),
        dict(key='stacks', title='Stacks and vents', cols=['Stack', 'Group', 'Fixtures', 'DFU', 'Vent'],
             rows=[(s['id'], [s['id'], s['name'], str(len(s['fixtures'])), str(sum(TABLE[FIX[f]['kind']][1] for f in s['fixtures'])), '3" VTR' if s['id'] != ISLAND else 'loop vent / AAV']) for s in STACKS]),
        dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the routing above, for pricing. The plumber takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=[
            (None, ['4" PVC DWV', f"{drain_lf['4\"'] * 1.15:.0f} ft", 'building drain, including 10 ft outside the rear wall (more to the sewer/septic)']),
            (None, ['3" PVC DWV', f"{drain_lf['3\"'] * 1.15:.0f} ft", 'trunk, branches, stack bases and toilet arms, + 15 %; plus ~60 ft for the four 3" vent stacks']),
            (None, ['2" PVC DWV', f"{drain_lf['2\"'] * 1.15 + 40:.0f} ft", 'floor drains, washer, + vents']),
            (None, ['1-1/2" PVC DWV', f"{drain_lf['1-1/2\"'] * 1.15 + 60:.0f} ft", 'lavs, tubs, kitchen sink, + vents']),
            (None, ['3/4" PEX', f"{pex_lf['3/4\"'] * 1.15:.0f} ft", 'group feeds and hose bibbs, + 15 %']),
            (None, ['1/2" PEX', f"{pex_lf['1/2\"'] * 1.15:.0f} ft", 'group feeds and runs to the fixtures, + 15 %']),
            (None, ['Pipe insulation, R-3, closed cell', f"{hot_lf * 1.1:.0f} ft", 'on every hot PEX run under the slab (IECC R403.5.3), + 10 %']),
            (None, ['Main manifold', '1', f"{len(SUP) + len(HOSE)} cold + {len(SUP)} hot outlets, main shutoff"]),
            (None, ['Group manifolds', str(sum(1 for g in SUP if not g.get('direct'))), '1/2" PEX, 3-5 ports with stops, in a vanity or behind an access panel']),
            (None, ['Water heater', '1', '50 gal, pan, expansion tank']),
            (None, ['Toilets', str(sum(1 for f in PLUMBED if f['kind'] == 'wc')), 'ADA height (A-5)']),
            (None, ['Tub/shower valves', str(sum(1 for f in PLUMBED if f['kind'] in ('tub', 'shower'))), 'pressure-balanced']),
            (None, ['Shower drains', '2', 'K-9136 (master), K-9135 (bath 1) per A-5']),
            (None, ['Floor drains', '2', 'garage and mechanical, K-9136 per A-5']),
            (None, ['Cleanouts', str(len(CLEANOUTS)), 'two-way at the exit, floor cleanouts at the junction and the head of the trunk']),
            (None, ['Hose bibbs', str(len(HOSE)), 'frost-free']),
        ]),
    ]
    summary = dict(fixtures=len(PLUMBED), dfu=dfu_total, wsfu=round(wsfu_c + wsfu_h, 1), stacks=len(STACKS), peak_gpm=supply_gpm,
                   drain_ft=round(sum(drain_lf.values())), pex_ft=round(sum(pex_lf.values())), exit_invert=round(-NET['exit_invert'], 2))
    lines = [dict(name=d['name'], pts=d['pts'], r=SIZE_R[d['size']]) for d in NET['pipes'].values()]
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, lines=lines, stacks=STACKS, hose=HOSE, plumb3d=model3d(NET, SUP, VENTS, wsfu_c + wsfu_h))


def model3d(NET, SUP, VENTS, wsfu):
    """The P-1 layer for the 3D model, the way Zero Rd draws it: pipes as tubes at their real depth. Drains under the slab at
    their sloped inverts with a riser up to each fixture, stacks up through the roof, vents up the walls and across the attic,
    the group PEX feeds under the slab with the short runs to each fixture. Each part is {m, r, pts: [[x, y, h], ...]} or
    a {shape} block, with the name/ref/text a pick shows; ref is the P-1 tag so 3D comments land on the same item."""
    out = []
    def tube(m, r, pts, ref, name, text): out.append(dict(m=m, r=r, pts=[[round(x, 2), round(y, 2), round(h, 3)] for x, y, h in pts], ref=ref, name=name, text=text))
    flat = lambda pts, h: [(x, y, h) for x, y in pts]
    sloped = lambda pts, zs, r: [(x, y, z + r) for (x, y), z in zip(pts, zs)]      # pipe centre = invert + radius
    depth = lambda z: ft_in(-z)
    # drains
    for d in NET['pipes'].values():
        r = SIZE_R[d['size']]
        tube('drain', r, sloped(d['pts'], d['z'], r), d['id'], f"{d['id']} · {d['name']}", f"{d['size']} under the slab, {dfu_into(d['id'])} DFU, invert {depth(d['z'][0])} at its head to {depth(d['z'][-1])}" + (' where it leaves the house at 25,0' if d['id'] == 'BD' else f" at {d['into']}"))
    for fid, a in NET['arms'].items():
        f, r = FIX[fid], SIZE_R[a['size']]
        name = f"{fid} · {f['name']}"
        if len(a['pts']) > 1: tube('drain', r, sloped(a['pts'], a['z'], r), fid, name, f"{a['size']} fixture drain under the slab to {a['pipe']}")
        top = {'wc': 0.15, 'drain': 0.0, 'tub': 0.3, 'washer': 2.8}.get(f['kind'], 1.4)
        tube('drain', 0.15 if f['kind'] == 'wc' else r, [(*f['at'], a['z'][0] + r), (*f['at'], top)], fid, name, f"{TABLE[f['kind']][2]} drain up through the slab to the trap, invert {depth(a['z'][0])}")
    # stacks through the roof (the island has a loop vent instead)
    for s in STACKS:
        if s['id'] == ISLAND: continue
        x, y = s['at']; l = NET['legs'][s['id']]
        if len(l['pts']) > 1: tube('drain', 0.13, sloped(l['pts'], l['z'], 0.13), s['id'], f"{s['id']} · {s['name']} stack base", f"3\" from the stack base to {s['pipe']}")
        tube('vent', 0.13, [(x, y, l['z'][0] + 0.13), (x, y, roof_over(s['at']) + 1.0)], s['id'], f"{s['id']} · {s['name']} stack", '3" stack: its base ties into the drain under the slab; up the wall and through the roof as the vent')
    # fixture vents
    for v in VENTS:
        f, r, (wx, wy) = v['fixture'], SIZE_R[v['size']] * 0.8, v['wall']
        name, text = f"{f['id']} · {f['name']} vent", f"{v['size']} vent" + (f", to the {v['to']} stack in the attic" if v['to'] else ' through the roof')
        low = vent_low(v, NET) if v.get('under') else 0.0 if f['kind'] in ('wc', 'tub', 'shower', 'drain') else 1.3
        if v.get('loop'):
            x, y = f['at']
            tube('vent', r, [(x + 0.3, y, low), (x + 0.3, y, 2.6), (x + 0.6, y + 0.3, 2.6), (x + 0.6, y + 0.3, low)], f['id'], f"{f['id']} · island loop vent", 'Loop vent: rises inside the island to the counter underside and loops back down (or an AAV where the AHJ allows)')
            tube('vent', r, flat([(x + 0.6, y + 0.3)] + v['under'][1:], low), f['id'], name, f"2\" vent under the slab at the sink drain's depth ({depth(low)}) to the laundry wall, then up to ST2's vent in the attic")
        elif v.get('under'):
            tube('vent', r, flat(v['under'], low), f['id'], name, text + f"; leaves the drain under the slab and runs to the wall first, {depth(low)} down, under the PEX")
        top = VENT_H if v['attic'] else roof_over(v['wall']) + 1.0
        tube('vent', r, [(wx, wy, low), (wx, wy, top)], f['id'], name, text + f", rising in the {'exterior' if v['ext'] else 'interior'} wall")
        if v['attic']: tube('vent', r, flat(v['attic'], VENT_H), f['id'], name, text + ', across the attic over the ceiling')
    # supply: 1" service up into the closet, the main manifold and the water heater, the PEX in its bands under R-1's boards and feeds
    mx, my = MANIFOLD
    tube('cold', PR['1"'], [(*SERVICE, -4.5), (*SERVICE, 3.4), (mx - 0.15, SERVICE[1], 3.4)], 'MAN', 'Water service, 1"', '1" service up through the slab to the main shutoff and the manifold; it comes in below the frost line (about 4\' in Powell), entry point TBD')
    out.append(dict(shape='box', m='cold', box=[mx - 0.15, my - 1.1, mx + 0.15, my + 1.1, 3.0, 4.2], ref='MAN', name='MAN · main manifold', text=f'Main manifold and shutoff, {wsfu:.1f} WSFU; one cold and hot pair to each fixture group, plus the hose bibbs'))
    wx, wy = WATER_HEATER
    out.append(dict(shape='cyl', m='hot', at=[wx, wy], r=0.95, h=[0.0, 5.0], ref='WH', name='WH · water heater, 50 gal', text='On a pan; T&P and pan drain to the closet floor drain; feeds the hot side of the manifold'))
    tube('hot', 0.06, [(wx, wy - 0.95, 4.6), (wx, my + 0.8, 4.6), (mx, my + 0.8, 4.6), (mx, my + 0.8, 4.2)], 'WH', 'WH · hot to the manifold', '3/4" hot from the water heater to the hot side of the manifold (clear of HS-1 on the east wall)')
    band = f"in the base course under the radiant boards and feed pairs"
    for g in SUP:
        gx, gy = g['at']
        direct = g.get('direct')
        ct = 1.7 if direct else 1.2   # the pair comes up into the vanity or wall to the group manifold (or the sink stops)
        tube('cold', PR[g['cold']], [(*COLD_DROP, 3.0), (*COLD_DROP, COLD_H)] + flat(g['cold_run'][1:], COLD_H) + [(gx, gy, ct)], g['id'], f"{g['id']} · cold feed, {g['name'].lower()}",
             f"{g['cold']} PEX cold from MAN, {plen(g['cold_run']):.0f} ft in one piece, {depth(COLD_H)} down {band}")
        tube('hot', PR[g['hot']], [(*HOT_DROP, 3.0), (*HOT_DROP, HOT_H)] + flat(g['hot_run'][1:], HOT_H) + [(gx + 0.3, gy + 0.3, ct)], g['id'], f"{g['id']} · hot feed, {g['name'].lower()}",
             f"{g['hot']} PEX hot from MAN, {plen(g['hot_run']):.0f} ft, insulated, {depth(HOT_H)} down {band}; about {g['wait_s']:.0f} s for hot water at the farthest fixture")
        if not direct:
            out.append(dict(shape='box', m='cold', box=[gx - 0.35, gy - 0.35, gx + 0.35, gy + 0.35, 1.2, 1.7], ref=g['id'], name=f"{g['id']} · {g['name']} manifold", text=f"Group manifold {g['where']}"))
        for fid, run in g['stubs'].items():
            f = FIX[fid]; top = STUB_TOP.get(f['kind'], 1.7)
            tube('cold', PR['1/2"'], [(gx, gy, 1.2), (gx, gy, COLD_H)] + flat(run[1:], COLD_H) + [(*run[-1], top)], fid, f"{fid} · cold to {f['name'].lower()}", f"1/2\" PEX cold from {g['id']}, {plen(run):.0f} ft, {depth(COLD_H)} down")
        for fid, run in g['hot_stubs'].items():
            f = FIX[fid]; top = STUB_TOP.get(f['kind'], 1.7)
            tube('hot', PR['1/2"'], [(*run[0], 1.2), (*run[0], HOT_H)] + flat(run[1:], HOT_H) + [(*run[-1], top)], fid, f"{fid} · hot to {f['name'].lower()}", f"1/2\" PEX hot from {g['id']}, {plen(run):.0f} ft, insulated, {depth(HOT_H)} down")
    for h in HOSE:
        run = h['run']
        tube('cold', PR['3/4"'], [(*COLD_DROP, 3.0), (*COLD_DROP, COLD_H)] + flat(run[1:], COLD_H) + [(*h['at'], 1.5)], h['id'], f"{h['id']} · hose bibb", f"{h['name']}: 3/4\" PEX cold, {plen(run):.0f} ft, {depth(COLD_H)} down under the slab")
        out.append(dict(shape='box', m='cold', box=[h['at'][0] - 0.2, h['at'][1] - 0.2, h['at'][0] + 0.2, h['at'][1] + 0.2, 1.35, 1.65], ref=h['id'], name=f"{h['id']} · hose bibb", text=h['name']))
    # floor drains (grates at the floor, on this layer and not with the fixtures) and cleanouts
    for f in PLUMBED:
        if f['kind'] == 'drain': out.append(dict(shape='cyl', m='drain', at=f['at'], r=0.27, h=[0.0, 0.04], ref=f['id'], name=f"{f['id']} · {f['name']}", text='Floor drain grate; trap and 2" drain under the slab (P-1)'))
    z_bd = NET['pipes']['BD']
    for id, at, text in CLEANOUTS:
        pid = 'BD' if id != 'CO3' else 'DT'
        d = NET['pipes'][pid]; i = _seg_of(d['pts'], at); z = d['z'][i + 1] + SLOPE[d['size']] * dist(at, d['pts'][i + 1])
        tube('drain', SIZE_R[d['size']], [(*at, z + SIZE_R[d['size']]), (*at, 0.05 if id != 'CO1' else -0.3)], id, f'{id} · cleanout', text)
    return out


if __name__ == '__main__':
    print(build()['summary'])
