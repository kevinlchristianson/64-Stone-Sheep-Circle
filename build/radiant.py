"""R-1 Radiant: PEX loops in the slab, manifolds, zones, flows and the manifold options.

The house heats from its slab: 1/2" PEX in a 4" slab over R-10 foam, laid as
counterflow spirals (supply and return interleaved, so the floor is even)
6" off the walls and clear of cabinets, tubs, the island and the hearth.
Spacing is 9" o.c. in the baths and wherever a room needs 15 Btu/h per sq ft
or more, 12" o.c. elsewhere. Room loads are M-1's (hvac.room_load, the same
envelope and Powell design temperature); the garage gets its own loops held
at 50°F. Loops are kept under 300' including leaders.

Zoning is by thermostat, not by manifold: every loop has a 24 V actuator on
its manifold port, and a thermostat drives whichever loops are its zone. So
manifolds go where they make the shortest loops, and zones follow how the
rooms are used. The options table routes the same loops to four manifold
layouts (including the owner's first sketch) and compares them.
"""
import math
from setlib import HOUSE, ROOMS, Sheet, ft_in, room_at
from climate import CLIMATE
import hvac

MAX_LOOP = 300.0          # ft of 1/2" PEX per loop, leaders included
DT = 10.0                 # design temperature drop per loop, °F
DOWN = 0.10               # share of each loop's heat lost down and out the slab edge, over R-10
R_SLAB = {6: 0.25, 9: 0.37, 12: 0.50}   # water to slab surface, h·sf·°F/Btu, 1/2" PEX in a 4" slab
R_COVER = 0.20            # hard-surface flooring assumed (tile, LVP, engineered wood); carpet is ~1.5
R_SURF = 0.50             # slab surface to room (2.0 Btu/h·sf·°F)
GARAGE_F = 50.0
RISE = 2.0                # ft of leader per end, slab up into the manifold
GARAGE_COLOR = '#2e7d32'

ZONES = {
    'Z1': dict(name='Master suite', color='#c62828', stat='T1', where='Master bed, interior wall by the hall door',
               rooms=['master_bed', 'master_bath', 'master_closet', 'master_hall']),
    'Z2': dict(name='Great room and utility', color='#e65100', stat='T2', where='Kitchen side of the living room, on the entry wall, away from the fireplace and the patio glass',
               rooms=['kitchen', 'dining', 'pantry', 'living', 'entry', 'laundry', 'powder', 'mud']),
    'Z3': dict(name='Bedroom wing and office', color='#1565c0', stat='T3', where='Bedroom hall, south end',
               rooms=['bed1', 'bath1', 'bed2', 'bed2_closet', 'bath2', 'bed3', 'bed3_closet', 'hall', 'office']),
    'ZG': dict(name='Garage (held at 50°F)', color=GARAGE_COLOR, stat='TG', where='Garage, wall by the mud room door',
               rooms=['garage']),
}
ZONE_OF = {r: z for z, v in ZONES.items() for r in v['rooms']}

# Panels: (room, x0, y0, x1, y1, spacing inches), already 6" off the wall faces and clear of
# cabinets, tubs, the island, the fridge and the hearth. A loop is one or more panels in series.
LOOPS = [
    # zone 1, master suite
    ('master_hall', 25.54, 18.33, 30.04, 21.33, 12), ('master_bed', 16.96, 0.96, 30.04, 17.04, 12), None,
    ('master_bath', 13.54, 14.17, 15.67, 23.67, 9), ('master_bath', 9.30, 6.04, 13.54, 23.67, 9), ('master_bath', 6.33, 17.13, 9.30, 23.67, 9), None,
    ('master_closet', 6.33, 24.96, 15.58, 33.34, 12), None,
    # zone 2, great room and utility
    ('dining', 31.33, 6.04, 43.21, 15.62, 6), None,
    ('kitchen', 31.33, 38.20, 43.21, 41.80, 12), ('kitchen', 33.42, 23.20, 36.24, 38.20, 12), None,
    ('kitchen', 31.33, 16.62, 43.21, 23.20, 12), ('kitchen', 41.12, 23.20, 43.21, 38.20, 12), None,
    ('laundry', 18.80, 18.50, 24.08, 29.30, 12), ('powder', 25.54, 22.63, 30.04, 27.15, 9), None,
    ('mud', 25.94, 36.34, 30.04, 41.71, 12), ('mud', 16.87, 30.76, 30.04, 36.34, 12), None,
    ('pantry', 34.71, 45.69, 43.21, 52.77, 9), ('entry', 44.50, 42.98, 50.58, 52.77, 9), None,
    ('living', 44.21, 17.35, 63.67, 27.30, 12), None,
    ('living', 44.21, 27.30, 58.90, 31.90, 12), None,
    ('living', 44.21, 31.90, 63.67, 41.98, 12), None,
    # zone 3, bedroom wing and office
    ('hall', 64.96, 19.44, 68.04, 39.48, 12), ('bath2', 69.33, 34.90, 79.70, 37.52, 9), ('bed3_closet', 78.25, 40.77, 82.48, 44.77, 9), None,
    ('bed1', 64.96, 6.04, 77.08, 18.44, 9), None,
    ('bed2_closet', 78.37, 16.63, 82.48, 20.73, 6), ('bath1', 78.37, 8.90, 82.48, 15.33, 6), ('bath1', 78.37, 6.04, 80.60, 8.90, 6), None,
    ('bed2', 69.33, 22.02, 82.48, 33.61, 12), None,
    ('bed3', 64.96, 40.77, 76.96, 52.77, 9), None,
    ('office', 51.87, 43.27, 63.67, 52.77, 12), None,
    # garage: 12" o.c., 12" back from the overhead doors, clear of the floor drain by 12"
    ('garage', 6.33, 34.63, 15.58, 37.63, 12), ('garage', 1.46, 37.63, 24.65, 43.00, 12), None,
    ('garage', 1.46, 43.00, 8.60, 66.63, 12), None,
    ('garage', 8.60, 43.00, 15.75, 66.63, 12), None,
    ('garage', 15.75, 43.00, 22.90, 66.63, 12), ('garage', 15.91, 66.63, 22.90, 69.13, 12), None,
    ('garage', 22.90, 43.00, 30.04, 66.63, 12), ('garage', 22.90, 66.63, 30.04, 69.13, 12), None,
]

# Heat source and manifold stations. 'out' is the axis the leaders leave the wall along.
HS = (33.55, 48.8)         # wall-hung on the mechanical closet's east wall (P-1's water manifold and heater share the closet)
T_SUP = 110.0              # design supply cap, °F: keeps a condensing boiler condensing and an air-to-water heat pump efficient
STATIONS = {
    'MF-1': dict(at=(20.6, 18.3), out='y', where='Laundry, on the north wall between the linen alcove and the dryer',
                 detail='Surface-mounted manifold cabinet on the laundry\'s north wall, between the master bath\'s linen alcove and the dryer. That wall is the staggered-stud sound wall to the master bed, so the cabinet is not recessed; leaders drop straight into the slab below.'),
    'MF-2': dict(at=(22.0, 37.6), out='y', where='Garage, on the mud room wall, beside MF-G',
                 detail='Surface-mounted cabinet on the garage face of the mud room wall, 4\' above the slab, beside MF-G; its leaders pass under the wall into the mud room and kitchen. Surface mounting keeps the garage fire separation whole.'),
    'MF-G': dict(at=(18.8, 37.6), out='y', where='Garage, on the mud room wall, beside MF-2',
                 detail='Surface-mounted cabinet on the garage face of the mud room wall, beside MF-2, with the garage\'s own pump P-RG and mixing valve.'),
    'MF-3': dict(at=(64.65, 25.6), out='x', where='Bedroom hall, recessed in the west wall north of the fireplace',
                 detail='Recessed manifold cabinet in the hall\'s west wall between the living room opening and the fireplace chase. A 2x4 wall takes a 3-1/2" deep cabinet; fur it to 2x6 locally if the chosen manifold needs more (S-1).'),
}
PREFER = {'master_closet': 'MF-1'}   # a near-tie that the zone's own manifold should win
MC = (33.6, 48.6)          # a manifold in the mechanical closet, for the options
MUD = (20.4, 37.6)         # the mud room wall station (MF-2 and MF-G)
OPTIONS = [
    ('O1', 'All manifolds in the mechanical closet, beside the heat source', {'MC': MC}),
    ('O2', 'Owner\'s first sketch: laundry corner, two on the garage side of the mud room wall, two in the bedroom hall beside the fireplace',
     {'K1': (17.4, 18.3), 'K2': (16.4, 37.6), 'K3': (64.65, 32.4)}),
    ('O3', 'Two stations: the mechanical closet, and the bedroom hall', {'MC': MC, 'MF-3': STATIONS['MF-3']['at']}),
    ('O4', 'Three stations: laundry north wall (MF-1), mud room wall in the garage (MF-2 and MF-G), bedroom hall north of the fireplace (MF-3)',
     {'MF-1': STATIONS['MF-1']['at'], 'MUD': MUD, 'MF-3': STATIONS['MF-3']['at']}),
    ('O5', 'O4 plus a fourth manifold in the mechanical closet for the kitchen, pantry and entry', {'MF-1': STATIONS['MF-1']['at'], 'MUD': MUD, 'MF-3': STATIONS['MF-3']['at'], 'MC': MC}),
]
DRAWN = 'O4'
MAX_PORTS = 24     # a station can stack two 12-port manifolds


# ---------------------------------------------------------------- geometry
def spiral(x0, y0, x1, y1, s, corner):
    """Counterflow spiral in a panel: supply spirals in at pitch 2s, return spirals out between.
    Starts at the panel corner nearest `corner` and ends s in from it on the diagonal."""
    W, D = x1 - x0, y1 - y0
    left = abs(corner[0] - x0) <= abs(corner[0] - x1); top = abs(corner[1] - y0) <= abs(corner[1] - y1)
    tx = lambda u: x0 + u if left else x1 - u
    ty = lambda v: y0 + v if top else y1 - v

    def inward(a, b, c, d, p):
        pts = [(a, b)]
        while True:
            if d - b < 0.05 or c - a < 0.05: break
            pts.append((a, d))
            pts.append((c, d))
            if d - b < p: break
            pts.append((c, b))
            if c - (a + p) < 0.05: break
            pts.append((a + p, b))
            a, b, c, d = a + p, b + p, c - p, d - p
        return pts

    p = 2 * s
    sup = inward(0, 0, W, D, p)
    ret = inward(s, s, W - s, D - s, p) if W > 2 * s and D > 2 * s else []
    if ret:
        e, f = sup[-1], ret[-1]
        mid = [(e[0], f[1])] if abs(e[0] - f[0]) > 1e-6 and abs(e[1] - f[1]) > 1e-6 else []
        path = sup + mid + ret[::-1]
    else:
        path = sup
    return [(tx(u), ty(v)) for u, v in path]


def lc(t): return t[:1].lower() + t[1:]


def plen(pts): return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))


def ortho(a, b, first):
    """a to b in two straight legs, along `first` axis first."""
    if abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6: return [a, b]
    return [a, (b[0], a[1]), b] if first == 'x' else [a, (a[0], b[1]), b]


def sample(pts, step=0.5):
    for a, b in zip(pts, pts[1:]):
        n = max(1, int((abs(a[0] - b[0]) + abs(a[1] - b[1])) / step))
        for i in range(n): yield (a[0] + (b[0] - a[0]) * (i + 0.5) / n, a[1] + (b[1] - a[1]) * (i + 0.5) / n), (abs(a[0] - b[0]) + abs(a[1] - b[1])) / n


# ---------------------------------------------------------------- loads per panel
def room_loads():
    out = {}
    for r in HOUSE['rooms']:
        if r['kind'] == 'outdoor': continue
        l = hvac.room_load(r)
        h = l['heat']
        if r['kind'] == 'garage':
            h *= (GARAGE_F - CLIMATE['heat_design_f']) / (CLIMATE['indoor_heat_f'] - CLIMATE['heat_design_f'])
        out[r['id']] = h
    return out


def split_loops():
    loops, cur = [], []
    for p in LOOPS:
        if p is None: loops.append(cur); cur = []
        else: cur.append(dict(room=p[0], rect=p[1:5], s=p[5]))
    return loops


def route(panels, mf, out):
    """Lay a loop from manifold point mf: leaders, panels in series, connectors. Returns geometry and lengths."""
    pos = mf; floor_pts = []; conns = []; cur = None
    for i, pn in enumerate(panels):
        x0, y0, x1, y1 = pn['rect']
        pts = spiral(x0, y0, x1, y1, pn['s'] / 12.0, pos)
        if cur is not None:
            conns.append(ortho(cur, pts[0], 'x' if abs(cur[0] - pts[0][0]) > abs(cur[1] - pts[0][1]) else 'y'))
        else:
            start = pts[0]
        floor_pts.append(pts); cur = pts[-1]; pos = cur
    lead_s = ortho(mf, start, out); lead_r = ortho(mf, cur, out)[::-1]
    in_floor = sum(plen(p) for p in floor_pts) + sum(plen(c) for c in conns)
    leader = plen(lead_s) + plen(lead_r) + 2 * RISE
    return dict(panels=floor_pts, conns=conns, lead=[lead_s, lead_r], in_floor=in_floor, leader=leader, total=in_floor + leader)


def head_ft(L, gpm): return L * 0.0118 * (gpm / 0.5) ** 1.75


def assign(loops, stations):
    """Each loop to the station that makes it shortest, within the port limit."""
    order = sorted(range(len(loops)), key=lambda i: -min(route(loops[i], at, 'x')['total'] for at in stations.values()))
    ports = {k: 0 for k in stations}; pick = {}
    for i in order:
        best = sorted(stations, key=lambda k: route(loops[i], stations[k], 'x')['total'])
        k = next(k for k in best if ports[k] < MAX_PORTS)
        pick[i] = k; ports[k] += 1
    return pick


def other_zone_lf(geo, zone):
    lf = 0.0
    for leg in geo['lead']:
        for (x, y), d in sample(leg):
            r = room_at(x, y)
            if r and ZONE_OF.get(r['id']) not in (None, zone): lf += d
    return lf


def evaluate(loops, stations, zones):
    pick = assign(loops, stations)
    geos = [route(loops[i], stations[pick[i]], 'x') for i in range(len(loops))]
    lens = [g['total'] for g in geos]
    feed = sum(abs(HS[0] - at[0]) + abs(HS[1] - at[1]) for k, at in stations.items() if abs(at[0] - HS[0]) + abs(at[1] - HS[1]) > 6 and k in pick.values())
    return dict(pick=pick, tube=sum(lens), leaders=sum(g['leader'] for g in geos), longest=max(lens), shortest=min(lens), over=sum(1 for L in lens if L > MAX_LOOP),
                cross=sum(other_zone_lf(g, zones[i]) for i, g in enumerate(geos)), feed=feed, stations=len(set(pick.values())))


# ---------------------------------------------------------------- the sheet
def build():
    sh = Sheet('R-1', 'Radiant floor', f"PEX loops in the slab, four thermostat zones, manifolds and flows at {CLIMATE['name']} design ({CLIMATE['heat_design_f']:.0f}°F).")
    sh.base()
    loads = room_loads()
    loops = split_loops()
    zones = [ZONE_OF[l[0]['room']] for l in loops]
    # tubed area per room, to share each room's load among its panels
    room_area = {}
    for l in loops:
        for pn in l:
            x0, y0, x1, y1 = pn['rect']; room_area[pn['room']] = room_area.get(pn['room'], 0) + (x1 - x0) * (y1 - y0)
    # drawn layout: garage loops on MF-G, the rest to whichever of MF-1, MF-2 and MF-3 makes them shortest
    house_st = {k: STATIONS[k]['at'] for k in ('MF-1', 'MF-2', 'MF-3')}
    hi = [i for i, z in enumerate(zones) if z != 'ZG']
    hp = assign([loops[i] for i in hi], house_st)
    pick = {i: hp[j] for j, i in enumerate(hi)}
    pick.update({i: PREFER[loops[i][0]['room']] for i in hi if loops[i][0]['room'] in PREFER})
    pick.update({i: 'MF-G' for i, z in enumerate(zones) if z == 'ZG'})
    # number loops by manifold, then position, so each manifold's ports read in order
    mf_order = ['MF-1', 'MF-2', 'MF-3', 'MF-G']
    idx = sorted(range(len(loops)), key=lambda i: (mf_order.index(pick[i]), zones[i], loops[i][0]['rect'][1], loops[i][0]['rect'][0]))
    picks, rows, L = {}, [], []
    for n, i in enumerate(idx, 1):
        lid = f'L{n}'; z = zones[i]; Z = ZONES[z]; mf = pick[i]; st = STATIONS[mf]
        geo = route(loops[i], st['at'], st['out'])
        area = sum((p['rect'][2] - p['rect'][0]) * (p['rect'][3] - p['rect'][1]) for p in loops[i])
        q_room = sum(loads[p['room']] * (p['rect'][2] - p['rect'][0]) * (p['rect'][3] - p['rect'][1]) / room_area[p['room']] for p in loops[i])
        q = q_room * (1 + DOWN)
        flux = q_room / area
        s = max(p['s'] for p in loops[i])
        t_room = GARAGE_F if z == 'ZG' else CLIMATE['indoor_heat_f']
        t_avg = t_room + flux * (R_SLAB[s] + (0 if z == 'ZG' else R_COVER) + R_SURF)
        t_surf = t_room + flux * R_SURF
        r_tot = R_SLAB[s] + (0 if z == 'ZG' else R_COVER) + R_SURF
        short = max(0.0, q_room - area * (T_SUP - DT / 2 - t_room) / r_tot) if z != 'ZG' else 0.0
        gpm = max(0.2, q / (500 * DT))
        hd = head_ft(geo['total'], gpm)
        rooms = []
        for p in loops[i]:
            nm = ROOMS[p['room']]['name']
            if nm not in rooms: rooms.append(nm)
        spacing = ', '.join(sorted({f'{p["s"]}"' for p in loops[i]}))
        L.append(dict(id=lid, i=i, zone=z, mf=mf, geo=geo, area=area, q=q, gpm=gpm, head=hd, t_avg=t_avg, t_surf=t_surf, rooms=rooms, spacing=spacing,
                      cross=other_zone_lf(geo, z), short=short))
    t_supply = min(T_SUP, math.ceil((max(l['t_avg'] for l in L if l['zone'] != 'ZG') + DT / 2) / 5) * 5)
    shorts = [l for l in L if l['short'] > 50]
    # draw: leaders, connectors and panels per loop, then manifolds and the heat source
    for l in L:
        c = ZONES[l['zone']]['color']; g = l['geo']
        title = (f"Loop {l['id']}, zone {l['zone'][1:]} ({ZONES[l['zone']]['name']}): {', '.join(l['rooms'])}. {g['in_floor']:.0f}' in the slab + {g['leader']:.0f}' of leaders = "
                 f"{g['total']:.0f}' of 1/2\" PEX at {l['spacing']} o.c., home run to {l['mf']}. {l['q']:,.0f} Btu/h, {l['gpm']:.2f} gpm on the flow meter, {l['head']:.1f} ft of head. One continuous coil, no fittings in the slab; tag both ends {l['id']}.")
        sh.open_group(l['id'], title)
        for pts in g['panels'] + g['conns'] + g['lead']:
            sh.path(pts, 'transparent', 7)
        for pts in g['panels'] + g['conns']:
            sh.path(pts, c, 1.1, extra=' class="pex"')
        for k, leg in enumerate(g['lead']):
            o = 0.18 if k else -0.18; along_y = STATIONS[l['mf']]['out'] == 'y'
            sh.path([(x + o * along_y, y + o * (not along_y)) for x, y in leg], c, 0.9, '5,1.5', extra=' class="lead"')
        x0, y0, x1, y1 = max(loops[l['i']], key=lambda p: (p['rect'][2] - p['rect'][0]) * (p['rect'][3] - p['rect'][1]))['rect']
        sh.add(f'<text x="{60 + (x0 + x1) / 2 * 11:.1f}" y="{60 + ((y0 + y1) / 2 + (1.4 if y1 - y0 > 4 else 0)) * 11:.1f}" font-size="7.5" font-weight="700" fill="{c}" text-anchor="middle" dominant-baseline="middle" stroke="#fff" stroke-width="2.5" paint-order="stroke">{l["id"]}</text>')
        sh.close_group()
        picks[l['id']] = dict(tag=l['id'], sub=f"Zone {l['zone'][1:]} · {ZONES[l['zone']]['name']}", fields=[
            ('Rooms', ', '.join(l['rooms'])), ('Tube', f"{g['total']:.0f}' of 1/2\" PEX: {g['in_floor']:.0f}' in the slab at {l['spacing']} o.c. + {g['leader']:.0f}' of leaders"),
            ('Manifold', f"{l['mf']}, {lc(STATIONS[l['mf']]['where'])}"), ('Heat', f"{l['q']:,.0f} Btu/h at design, {l['area']:.0f} sq ft of tubed floor"),
            ('Flow', f"{l['gpm']:.2f} gpm on the flow meter, {l['head']:.1f} ft of head in the tube"),
            ('Water / floor', f"needs about {l['t_avg']:.0f}°F average water; floor surface about {l['t_surf']:.0f}°F at design"),
            ('Thermostat', f"{ZONES[l['zone']]['stat']}, actuator on {l['mf']} port {l['id']}")])
    # feed pairs from the heat source to the remote manifolds
    feeds = []
    FEED_ROUTES = {
        'MF-1': [HS, (32.0, HS[1]), (32.0, 21.0), (20.6, 21.0), STATIONS['MF-1']['at']],
        'MF-2': [HS, (32.0, HS[1]), (32.0, 44.0), (20.4, 44.0), MUD],
        'MF-3': [HS, (HS[0], 44.6), (44.2, 44.6), (44.2, 42.3), (64.65, 42.3), STATIONS['MF-3']['at']],
    }
    for k, pts in FEED_ROUTES.items():
        lf = plen(pts)
        on = [k, 'MF-G'] if k == 'MF-2' else [k]
        gpm = sum(l['gpm'] for l in L if l['mf'] in on)
        to = 'MF-2 and MF-G' if k == 'MF-2' else k
        feeds.append(dict(id='F-' + k[3:], mf=k, to=to, pts=pts, lf=lf, gpm=gpm))
        sh.open_group('F-' + k[3:], f"1\" PEX supply and return pair, HS-1 to {to}: about {lf:.0f}' each way, {gpm:.1f} gpm, insulated end to end.")
        sh.path(pts, 'transparent', 7); sh.path(pts, '#6a1b9a', 3.0); sh.path(pts, '#fff', 1.0)
        sh.close_group()
        picks['F-' + k[3:]] = dict(tag='F-' + k[3:], sub=f'Feed pair to {to}', fields=[('Pipe', '1" PEX supply + return, closed-cell insulated end to end, under the slab in the foam layer'),
                                                                                    ('Run', f'about {lf:.0f}\' each way from HS-1'), ('Flow', f'{gpm:.1f} gpm with every loop on {to} calling')])
    for k, st in STATIONS.items():
        x, y = st['at']; n = sum(1 for l in L if l['mf'] == k)
        horiz = st['out'] == 'y'
        w, h = (2.6, 0.9) if horiz else (0.9, 2.6)
        title = f"{k}: {n}-loop stainless manifold with flow meters and 24 V actuators, {lc(st['where'])}. {st['detail']}"
        sh.open_group(k, title, hit=(x, y, 1.4))
        sh.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, '#fff', '#222', 1.3, '4,2')
        sh.text(x, y, k, 6.5, '#222', '700', rot=0 if horiz else -90, layer='disc')
        sh.close_group()
        loops_on = [l['id'] for l in L if l['mf'] == k]
        picks[k] = dict(tag=k, sub=st['where'], fields=[('Manifold', f'{n}-loop stainless, flow meters, isolation ball valves, purge/fill and a 24 V actuator on every return port'),
                                                         ('Loops', ', '.join(loops_on)), ('Flow', f"{sum(l['gpm'] for l in L if l['mf'] == k):.1f} gpm with all loops calling"),
                                                         ('Where', st['detail'])])
    x, y = HS
    sh.open_group('HS-1', 'HS-1, condensing boiler for the slab, with the system pump, mixing and the zone controller', hit=(x, y, 1.2))
    sh.rect(x - 1.1, y - 0.6, x + 1.1, y + 0.6, '#fff', '#6a1b9a', 1.6); sh.text(x, y, 'HS-1', 6, '#6a1b9a', '700', layer='disc')
    sh.close_group()
    picks['HS-1'] = dict(tag='HS-1', sub='Mechanical closet', fields=[
        ('Equipment', 'Wall-hung condensing boiler with outdoor reset, on natural gas or propane (owner\'s picks, 2026-10-13; matches E-1)'),
        ('Output', f"{sum(l['q'] for l in L):,.0f} Btu/h with every zone calling, {sum(l['q'] for l in L if l['zone'] != 'ZG'):,.0f} Btu/h for the house alone"),
        ('Water', f"{t_supply:.0f}°F supply at {CLIMATE['heat_design_f']:.0f}°F outside, reset down to about 80°F at 50°F outside; garage loops mix down to about 70°F"),
        ('Pumps', 'P-R1: ECM circulator on constant ΔP for MF-1, MF-2 and MF-3; P-RG for MF-G on its own mixing valve'),
        ('Controls', '24 V zone controller with T1, T2, T3 and TG; outdoor sensor on the shaded rear wall')])
    # thermostats
    stats = {'T1': (27.6, 16.6), 'T2': (46.0, 41.6), 'T3': (66.5, 39.2), 'TG': (24.2, 40.2)}
    for z, Z in ZONES.items():
        x, y = stats[Z['stat']]
        sh.tag(x, y, Z['stat'], Z['color'], id=Z['stat'], title=f"{Z['stat']}, zone {z[1:]} thermostat ({Z['name']}): {Z['where']}.", r=0.62, size=6)
        lz = [l for l in L if l['zone'] == z]
        picks[Z['stat']] = dict(tag=Z['stat'], sub=f"Zone {z[1:]} · {Z['name']}", fields=[('Where', Z['where']), ('Loops', ', '.join(l['id'] for l in lz)),
                                                                                       ('Manifolds', ', '.join(sorted({l['mf'] for l in lz}))), ('Load', f"{sum(l['q'] for l in lz):,.0f} Btu/h at design")])
    # legend: Zero Rd's strip under the plan
    legend = [(Z['color'], f"Zone {z[1:]}, {Z['name']} ({Z['stat']})") for z, Z in ZONES.items()] + [('#6a1b9a', '1" feed pair from HS-1')]
    sym = [(f'<line x1="-12" y1="0" x2="12" y2="0" stroke="{c}" stroke-width="1.6"/>', t) for c, t in legend[:-1]]
    sym += [('<line x1="-12" y1="0" x2="12" y2="0" stroke="#555" stroke-width="1" stroke-dasharray="5,1.5"/>', 'leader pair (drawn spread out)'),
            ('<line x1="-12" y1="0" x2="12" y2="0" stroke="#6a1b9a" stroke-width="3"/><line x1="-12" y1="0" x2="12" y2="0" stroke="#fff" stroke-width="1"/>', legend[-1][1]),
            ('<rect x="-9" y="-4" width="18" height="8" fill="#fff" stroke="#222" stroke-dasharray="3,2"/>', 'manifold')]
    sh.legend(sym)
    # options
    opt_rows = []
    house_loops = [l for l, z in zip(loops, zones)]
    for oid, desc, stns in OPTIONS:
        ev = evaluate(house_loops, stns, zones)
        star = ' ★' if oid == DRAWN else ''
        opt_rows.append((None, [oid + star, desc, f"{ev['tube']:,.0f}'", f"{ev['leaders']:,.0f}'", f"{ev['longest']:.0f}' / {ev['shortest']:.0f}'", str(ev['over']),
                                f"{ev['cross']:.0f}'", f"{ev['feed']:.0f}' × 2" if ev['feed'] else 'none', str(ev['stations'])]))
    tot_tube = sum(l['geo']['total'] for l in L)
    tot_q = sum(l['q'] for l in L); tot_gpm = sum(l['gpm'] for l in L)
    worst = max(L, key=lambda l: l['head'])
    feed_lf = sum(f['lf'] for f in feeds)
    loop_rows = [(l['id'], [l['id'], l['zone'][1:], ', '.join(l['rooms']), l['mf'], l['spacing'], f"{l['geo']['in_floor']:.0f}'", f"{l['geo']['leader'] / 2:.0f}'", f"{l['geo']['total']:.0f}'",
                           f"{l['q']:,.0f}", f"{l['gpm']:.2f} gpm", f"{l['head']:.1f} ft", f"{l['t_surf']:.0f}°F"]) for l in L]
    for z, Z in ZONES.items():
        lz = [l for l in L if l['zone'] == z]
        loop_rows.append((Z['stat'], [f"Zone {z[1:]}", z[1:], Z['name'], ', '.join(sorted({l['mf'] for l in lz})), '', f"{len(lz)} loops", '', f"{sum(l['geo']['total'] for l in lz):,.0f}'",
                                       f"{sum(l['q'] for l in lz):,.0f}", f"{sum(l['gpm'] for l in lz):.1f} gpm", '', '']))
    mf_rows = [(k, [k, f"{sum(1 for l in L if l['mf'] == k)} loops: " + ', '.join(l['id'] for l in L if l['mf'] == k), st['where'], ', '.join(sorted({l['zone'][1:] for l in L if l['mf'] == k})),
                    next(f"1\" pair F-{('2' if k == 'MF-G' else k[3:])}, {f['lf']:.0f}' each way" for f in feeds if f['mf'] == ('MF-2' if k == 'MF-G' else k))]) for k, st in STATIONS.items()]
    cross_lf = sum(l['cross'] for l in L)
    notes = [
        'Positions are taped from the nearest wall face, exterior walls first. Every panel stops 6" off the walls, so interior wall plates fasten in that band; mark every tube crossing under a wall line on the vapor barrier and keep shots and anchors 12" from it.',
        f"Tube: 1/2\" O2-barrier PEX in counterflow spirals (supply in, return out between), tied to the mesh at mid-depth of a 4\" slab. {sum(1 for l in L if l['spacing'] != '12"')} loops run at 9\" o.c. or 6\" (baths, and rooms needing 15 Btu/h per sq ft or more; 6\" in the dining room and Bath 1), the rest at 12\". One continuous coil per loop, no fittings in the slab. Tag both ends of every loop at its manifold.",
        'No tube under the kitchen base cabinets, island, fridge or back cabinet, the tubs, the vanities, the laundry cabinets or the fireplace hearth. Keep tube 6" from toilet flanges and 12" from floor and shower drains; the showers\' floors are heated.',
        'Under the slab: R-10 (2") rigid foam under the whole heated slab and the garage slab, with R-10 at the slab edge (IECC 2021 zone 6 for a heated slab), and a 10-mil vapor barrier over the foam.',
        f"Zoning is by thermostat: four zones (master suite, great room and utility, bedroom wing and office, garage) on 24 V actuators at each loop's manifold port, so a room can get its own thermostat later by rewiring, without new tube.",
        'Manifolds, three stations: ' + '; '.join(f"{k} ({lc(STATIONS[k]['where'])}) serves " + ', '.join(sorted({r for l in L if l['mf'] == k for r in l['rooms']}, key=lambda n: [r['name'] for r in HOUSE['rooms']].index(n))) for k in STATIONS) + '. HS-1 in the mechanical closet feeds all three.',
        f"Leaders run in the slab as tight pairs (drawn spread out). Sleeve them in 3/8\" foam where they pass under another zone ({cross_lf:.0f}' in all) and wherever they cross a sawcut control joint. Feed pairs from HS-1 to the three stations are 1\" PEX, insulated end to end, {feed_lf:.0f}' each way in all.",
        f"Flow: {tot_gpm:.1f} gpm with every loop calling, each loop set on its flow meter at a {DT:.0f}°F drop. Design heat {tot_q:,.0f} Btu/h, of which {sum(l['q'] for l in L if l['zone'] == 'ZG'):,.0f} is the garage at {GARAGE_F:.0f}°F; {DOWN * 100:.0f}% is added for heat lost down and out the edge.",
        f"Water: {t_supply:.0f}°F supply at {CLIMATE['heat_design_f']:.0f}°F outside, reset lower as it warms, so any low-temperature source can run it. Floor surfaces stay at or under {max(l['t_surf'] for l in L if l['zone'] != 'ZG'):.0f}°F."
        + (' At that supply ' + ', '.join(f"{l['id']} ({', '.join(l['rooms'])}) falls about {l['short']:,.0f} Btu/h short" for l in shorts) + ' at design; see the open items.' if shorts else ''),
        f"Pump: the hardest loop is {worst['id']} at {worst['head']:.1f} ft in the tube; add about 3 ft for the feed pair, manifold and actuator. A constant-ΔP ECM circulator at about {math.ceil(max(l['head'] for l in L) + 3)} ft covers it.",
        'Pressure test every loop at 100 psi water or 60 psi air for 24 hours before the pour and keep it under pressure through the pour. Photograph the layout with a tape in frame before concrete.',
    ]
    open_items = [f"{l['id']} ({', '.join(l['rooms'])}): the floor carries all but about {l['short']:,.0f} Btu/h of the room at {CLIMATE['heat_design_f']:.0f}°F with {T_SUP:.0f}°F water. Add a small electric towel warmer, or run the boiler hotter on the coldest days." for l in shorts] + [
        'Boiler model: HS-1 is a condensing boiler on natural gas or propane (decided 2026-10-13). Pick a combi or a boiler with an indirect tank if it should also make the domestic hot water and replace P-1\'s 50 gal heater; propane needs the boiler\'s LP conversion kit.',
        'Garage: kept at 50°F on its own manifold, pump and thermostat. Decide whether it runs a glycol mix behind a plate heat exchanger, which protects it if the house loses power in a cold snap with the doors open.',
        'Flooring: the loops assume hard-surface floors. Carpet in a bedroom needs about 10°F warmer water for that loop, or 9" spacing there.',
        'Mechanical closet: HS-1, pump P-R1 and the zone controller share it with P-1\'s water manifold and water heater; that is why no manifold is drawn there (O5 in the options shows the fourth manifold saves little tube). A combi boiler removes the water heater and makes room.',
        'MF-3 cabinet depth in the hall\'s 2x4 west wall (S-1), and the boiler, pump and zone controller circuits (E-1).',
    ]
    sh.title_block([f"{len(L)} loops, {tot_tube:,.0f}' of 1/2\" PEX, {len(STATIONS)} manifolds.", 'Red zone 1, orange zone 2, blue zone 3, green garage.',
                    f"{tot_q / 1000:,.0f} kBtu/h at design, {t_supply:.0f}°F supply.", 'Zones are thermostats on loop actuators, not manifolds.'])
    coils = math.ceil(tot_tube * 1.05 / 1000) * 2
    tables = [
        dict(key='loops', title='Loop schedule', lede='Leader is each way. Heat includes the share lost downward. Pick a row to find the loop.',
             cols=['Loop', 'Zone', 'Rooms', 'Manifold', 'Spacing', 'In slab', 'Leader', 'Total', 'Btu/h', 'Flow', 'Head', 'Floor'], rows=loop_rows),
        dict(key='manifolds', title='Manifolds', cols=['Tag', 'Loops', 'Where', 'Zones', 'Feed'], rows=mf_rows),
        dict(key='options', title='Manifold options',
             lede='The same loops routed to each layout, every loop to its nearest station (two 12-port manifolds at most per station). Leaders count both ends and the 2\' rise at the manifold. ★ is drawn.',
             cols=['Option', 'Layout', '1/2" PEX', 'Leaders', 'Longest / shortest loop', 'Loops over 300\'', 'Leader under another zone', 'Feed pairs', 'Stations'], rows=opt_rows),
        dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the drawing geometry, for pricing. The installer takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=[
            (None, ['1/2" O2-barrier PEX, 1,000\' coils', f'{coils // 2} coils', f"{tot_tube:,.0f}' + 5% waste; one length per loop, no splices"]),
            (None, ['1" PEX supply + return, insulated', f"{feed_lf * 2:.0f} lf", 'HS-1 to the three manifold stations, under the slab']),
            (None, ['Stainless manifolds with flow meters', f"{len(STATIONS)}", ', '.join(f"{k} {sum(1 for l in L if l['mf'] == k)}-loop" for k in STATIONS)]),
            (None, ['24 V thermal actuators', str(len(L)), 'one per loop']),
            (None, ['Zone controller + thermostats', '1 + 4', 'T1, T2, T3, TG; outdoor reset sensor']),
            (None, ['Circulators', '2', 'P-R1 constant ΔP for the house, P-RG for the garage with its mixing valve']),
            (None, ['Manifold cabinets', str(len(STATIONS)), 'recessed at MF-3, surface at MF-1 (sound wall), MF-2 and MF-G']),
            (None, ['R-10 rigid foam, 2"', f"{HOUSE['totals']['heated_gross_sf'] + HOUSE['totals']['garage_gross_sf']:,} sf", 'under the heated slab and the garage, plus the slab edge']),
            (None, ['10-mil vapor barrier', f"{(HOUSE['totals']['heated_gross_sf'] + HOUSE['totals']['garage_gross_sf']) * 1.1:,.0f} sf", 'over the foam, lapped and taped']),
            (None, ['Foam sleeve 3/8" for 1/2" PEX', f"{cross_lf * 1.1 + 40:.0f} lf", 'leaders under other zones and at control joints']),
            (None, ['PEX staples / ties, 18" o.c.', f"{tot_tube / 1.5 / 1000:.1f}k", 'to the mesh or foam']),
        ]),
    ]
    summary = dict(loops=len(L), tube_ft=round(tot_tube), heat=round(tot_q), house_heat=round(sum(l['q'] for l in L if l['zone'] != 'ZG')), gpm=round(tot_gpm, 1), supply_f=t_supply, manifolds=len(STATIONS))
    lines = []
    for l in L:
        nm = f"{l['id']} · zone {l['zone'][1:]}, {', '.join(l['rooms'])}"
        txt = f"{l['geo']['total']:.0f}' of 1/2\" PEX at {l['spacing']} o.c. to {l['mf']}, {l['gpm']:.2f} gpm (R-1)"
        for pts in l['geo']['panels'] + l['geo']['conns']:
            lines.append(dict(layer='radiant', name=nm, text=txt, pts=pts, h=0.06, r=0.05, color=ZONES[l['zone']]['color']))
        for leg in l['geo']['lead']:
            lines.append(dict(layer='radiant', name=nm + ' leader', text=txt, pts=leg, h=0.06, r=0.05, color=ZONES[l['zone']]['color']))
    for f in feeds:
        lines.append(dict(layer='radiant', name=f"{f['id']} · 1\" feed pair to {f['mf']}", text=f"about {f['lf']:.0f}' each way, insulated (R-1)", pts=f['pts'], h=0.06, r=0.09, color='#6a1b9a'))
    items = [dict(layer='radiant', x=st['at'][0], y=st['at'][1], h=2.6, size=1.2, name=f"{k} · radiant manifold", text=st['detail']) for k, st in STATIONS.items()]
    items.append(dict(layer='radiant', x=HS[0], y=HS[1], h=3.5, size=1.4, name='HS-1 · condensing boiler', text='Gas or propane condensing boiler for the slab, with the pumps and zone controller (R-1)'))
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, legend=legend, lines=lines, items=items, loops=L)


if __name__ == '__main__':
    b = build()
    print(b['summary'])
    for l in b['loops']:
        print(f"{l['id']:4s} {l['zone']} {l['mf']:5s} {l['spacing']:8s} {l['geo']['in_floor']:5.0f} {l['geo']['leader']:4.0f} {l['geo']['total']:5.0f} {l['q']:6.0f} {l['gpm']:.2f} {l['head']:.1f} {l['t_avg']:.0f} {l['t_surf']:.0f} {l['cross']:.0f} {l['rooms']}")
    for r in b['tables'][2]['rows']: print(r[1])
