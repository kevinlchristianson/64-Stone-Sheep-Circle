"""M-1 HVAC: room-by-room loads and a ductless mini-split layout (outdoor units, wall heads, line sets).

Loads are a simplified Manual J: each room's exterior walls, windows, doors,
ceiling and slab edge from plan/house.json, times a U-value, times the
design temperature difference, plus air leakage shared by exterior wall
area, and for cooling solar gain through the glass, people and appliances.
Envelope values are IECC 2021 climate zone 6 minimums for a new house
(build/climate.py), so the numbers move when the location or the insulation
is settled. Equipment: two cold-climate multi-zone mini-split heat pumps with
high-wall heads, no ducts; the radiant slab (R-1) is the heat.
"""
import math
from setlib import HOUSE, ROOMS, Sheet, ft_in, centroid, bbox, room_at, px, py
from climate import CLIMATE, ENVELOPE

H = HOUSE['meta']['ceiling_ft']
VAULT = {'kitchen', 'living'}
HEATED = [r for r in HOUSE['rooms'] if r['kind'] not in ('garage', 'outdoor')]


def exposures(room):
    """Each wall edge of the room that faces outside (or the garage, a buffer)."""
    out = []
    p = room['poly']
    cx, cy = centroid(room)
    for i in range(len(p)):
        (x0, y0), (x1, y1) = p[i], p[(i + 1) % len(p)]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 0.5: continue
        horiz = abs(y1 - y0) < 1e-6
        # look across the wall (0.8 ft past a 2x6) at a few points
        hits = []
        for f in (0.2, 0.5, 0.8):
            mx, my = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            if horiz: sx, sy = mx, my + (0.8 if my > cy else -0.8)
            else: sx, sy = mx + (0.8 if mx > cx else -0.8), my
            other = room_at(sx, sy)
            hits.append('outside' if other is None or other['kind'] == 'outdoor' else 'garage' if other['kind'] == 'garage' else 'inside')
        kind = max(set(hits), key=hits.count)
        if kind == 'inside': continue
        out.append(dict(kind=kind, horiz=horiz, line=y0 if horiz else x0, a0=min(x0, x1) if horiz else min(y0, y1), a1=max(x0, x1) if horiz else max(y0, y1), len=L))
    return out


def openings_on(room, e):
    ops = []
    for o in HOUSE['windows'] + [d for d in HOUSE['doors'] if d.get('ext') or d['kind'] == 'fire']:
        if o['axis'] != ('y' if e['horiz'] else 'x'): continue
        if abs(o['at'] - e['line']) > 0.7: continue
        if o['span'][0] < e['a0'] - 0.3 or o['span'][1] > e['a1'] + 0.3: continue
        ops.append(o)
    return ops


def room_load(r):
    C, E = CLIMATE, ENVELOPE
    dTh = C['indoor_heat_f'] - C['heat_design_f']; dTc = C['cool_design_f'] - C['indoor_cool_f']
    ex = exposures(r)
    wall = glass = door = slab = garage_wall = 0.0
    sun = 0.0
    for e in ex:
        ops = openings_on(r, e)
        g = sum(o['w'] * o['h'] for o in ops if 'head' in o)
        d = sum(o['w'] * o['h'] for o in ops if 'head' not in o and o['kind'] != 'overhead')
        if e['kind'] == 'garage':
            garage_wall += e['len'] * H - d; door += d
        else:
            wall += e['len'] * H - g - d; glass += g; door += d; slab += e['len']
            sun += g
    area = r['area_sf']
    vault = r['id'] in VAULT
    ceil = area * (math.hypot(12, 4) / 12 if vault else 1)
    vol = area * (H + (2.5 if vault else 0))
    UA = dict(walls=wall * E['wall_u'], windows=glass * E['window_u'], doors=door * E['door_u'],
              ceiling=ceil * (E['vault_u'] if vault else E['ceiling_u']), slab=slab * E['slab_f'], garage=garage_wall * E['wall_u'] * 0.5)
    ua = sum(UA.values())
    inf_cfm = vol * E['ach_nat'] / 60
    heat = ua * dTh + 1.08 * inf_cfm * dTh * C['altitude_factor']
    cool = (UA['walls'] + UA['doors'] + UA['garage']) * (dTc + 8) + UA['ceiling'] * (dTc + 30) + UA['windows'] * dTc \
        + sun * E['window_shgc'] * C['solar_btu_sf'] + 1.08 * inf_cfm * dTc * C['altitude_factor']
    people = {'bed': 2, 'living': 3, 'kitchen': 2}.get(r['kind'], 0)
    if r['id'] == 'master_bed': people = 2
    cool += people * 230 + (1200 if r['id'] == 'kitchen' else 0) + (300 if r['id'] in ('office', 'living') else 0) + (400 if r['id'] == 'laundry' else 0)
    return dict(id=r['id'], name=r['name'], area=area, ext_wall=round(wall), glass=round(glass), heat=heat, cool=cool, ua=ua, exposures=ex, vol=vol)


# ---------------------------------------------------------------- mini-split layout
# Two cold-climate multi-zone heat pumps, no ducts. The radiant slab (R-1) is the heat;
# the mini-splits are the cooling and a second, fast-acting heat source in the rooms they serve.
# Plan feet as everywhere else: X to the right (garage side is left), Y down the sheet (rear at the top).
# Second pass (owner, 2026-10-13): units on a pad against any exterior wall, line sets by the shortest route,
# heads as drawn in the first pass.
LS = '#b06a2c'       # refrigerant line sets
CD = '#2c6aa0'       # condensate
EQ = '#333'          # equipment
ZONE = {'CU-1': '#e3a05a', 'CU-2': '#7fa6c9'}
ATTIC = 9.6          # line sets ride on the ceiling framing under the attic insulation
LH = 8.2             # outside, in a line-hide along the wall, just above the window heads
HEAD_TOP = 8.5       # 6" below the 9' ceiling
HEAD_IN = 8.0        # where the line set enters the back of a head
HEAD_W, HEAD_H, HEAD_D = 2.75, 0.95, 0.75
SIZES = [6000, 9000, 12000, 15000, 18000]
MULTI = {2: 18000, 3: 24000, 4: 36000, 5: 42000}  # smallest common cold-climate multi-zone for a port count
AT_5F, AT_DESIGN = 1.0, 0.75   # share of rated heat a cold-climate (Hyper-Heat / XLTH class) multi-zone keeps at 5 °F and at about -11 °F
CU_W, CU_D, CU_H = 3.1, 1.17, 2.75
OFF = 2.5            # back of the unit off the wall: outside the 1'-6" eave drip line, with service room behind

UNITS = {
    # in the notch on the rear of the house between the master bedroom's bump-out and the covered patio: a 13' x 5' alcove
    # nobody looks into, with the dining attic right above it, so the three heads are all within about 70 ft
    'CU-1': dict(at=(40.5, 5.08 - OFF - CU_D / 2), axis='y', wall=5.08, stand=1.0, sleeve=(42.9, 5.08), ds=(31.0, 3.5, 'y'),
                 sub='Rear alcove, against the dining room\'s rear wall',
                 why='The rear of the house steps in 5\' between the master bedroom and the covered patio, which leaves a 13\' x 5\' alcove that is out of sight from the yard, the front and the patio. The dining attic is right above it, so the master and dining sets are short and the living set gets to the vault without going around anything. It discharges north into the open yard. The nearest bedroom window (the master\'s) is about 11 ft away around a corner; the patio edge is 2 ft east of the unit, so it is heard on the patio when it runs.'),
    # on the bedroom wing's right wall at Bath 2, a blank wall between the Bedroom 2 windows and the Bedroom 3 closet
    'CU-2': dict(at=(83.44 + OFF + CU_D / 2, 37.2), axis='x', wall=83.44, stand=1.0, sleeve=(83.44, 37.2), ds=(83.44, 40.6, 'x'),
                 sub='Right side yard, on the Bath 2 wall',
                 why='Bath 2\'s outside wall is the blank stretch of the bedroom wing\'s right wall nearest the middle of the three heads: Bedroom 2\'s head is on the same wall 9 ft north, Bedroom 3\'s is around the closet corner 12 ft south, and only Bedroom 1 needs an attic run. The nearest bedroom window (Bedroom 2\'s W14) is 3 ft north of the unit; the Bath 1 wall is the quieter spot, 8 ft from any bedroom window, at the cost of about 10 ft more line.'),
}

# (id, room, wall face side, centre along the wall, unit, rooms it serves, condensate, controller spot)
HEADS = [
    ('IU-1', 'master_bed', 'n', 23.5, 'CU-1', ['master_bed', 'master_bath', 'master_closet', 'master_hall'], 'gravity', (25.0, 17.42)),
    ('IU-2', 'dining', 'w', 12.6, 'CU-1', ['dining'], 'pump', (30.95, 16.4)),
    ('IU-3', 'living', 'e', 37.0, 'CU-1', ['living', 'kitchen', 'entry', 'pantry'], 'pump', (64.05, 40.4)),
    ('IU-4', 'bed1', 'n', 71.02, 'CU-2', ['bed1', 'bed1_closet', 'bath1'], 'gravity', (69.4, 18.82)),
    ('IU-5', 'bed2', 'e', 27.81, 'CU-2', ['bed2', 'bed2_closet', 'bath2'], 'gravity', (68.95, 30.3)),
    ('IU-6', 'bed3', 'e', 49.5, 'CU-2', ['bed3', 'bed3_closet'], 'gravity', (69.2, 40.39)),
]
WHY = {
    'IU-1': 'On the rear wall between the two windows, throwing toward the door; the rear wall is exterior, so the condensate drains straight out by gravity.',
    'IU-2': 'The dining room\'s rear and patio walls are all windows, so the head goes on the wall it shares with the master bedroom, throwing toward the patio windows; condensate pump in the wall.',
    'IU-3': 'High on the right wall of the living room, 5\'-6" past the fireplace, throwing across the living room into the kitchen. Its line set comes down this wall from the bedroom-hall attic; condensate pump in the wall.',
    'IU-4': 'On the rear wall between the two windows; exterior, gravity condensate.',
    'IU-5': 'On the right wall between the two windows; exterior, gravity condensate.',
    'IU-6': 'On the right wall (the part past the closet), throwing across the room; exterior, gravity condensate.',
}
# Line-set routes as 3D points (x, y, height) from the back of the outdoor unit to the back of the head.
# CU-1: a line-hide along the base of the dining wall to a sleeve in the full-height stud bay between window W6
# and the patio corner, up inside that bay to the dining attic, then on the ceiling framing. The living set rides
# the low edge of the kitchen/living vault (the scissor bottom chord is only ~6" up at Y 17.5) into the Bedroom 1
# and hall attics and drops in the living room's right wall.
# CU-2: the Bedroom 2 and 3 heads are on exterior walls, so their sets stay outside in a line-hide (the Bedroom 3
# set turns the closet's two corners); only Bedroom 1 goes through a sleeve and the attic.
def _cu1(tail):
    return [(40.5, 5.08 - OFF, 2.0), (40.5, 4.9, 2.0), (42.9, 4.9, 2.0), (42.9, 5.31, 1.5), (42.9, 5.31, ATTIC), (42.9, 5.8, ATTIC)] + tail
def _cu2_attic(tail):
    return [(83.44 + OFF, 37.2, 2.0), (83.44, 37.2, 1.5), (83.21, 37.2, 1.5), (83.21, 37.2, ATTIC), (82.4, 37.2, ATTIC)] + tail
def _cu2_out(tail):
    return [(83.44 + OFF, 37.2, 2.0), (83.65, 37.2, 2.0), (83.65, 37.2, LH)] + tail
ROUTES = {
    'IU-1': _cu1([(30.95, 5.8, ATTIC), (30.3, 5.8, ATTIC), (30.3, 1.0, ATTIC), (23.5, 1.0, ATTIC), (23.5, 0.23, ATTIC), (23.5, 0.23, HEAD_IN), (23.5, 0.46, HEAD_IN)]),
    'IU-2': _cu1([(30.95, 5.8, ATTIC), (30.7, 12.6, ATTIC), (30.7, 12.6, HEAD_IN), (30.833, 12.6, HEAD_IN)]),
    'IU-3': _cu1([(43.3, 17.5, ATTIC + 0.3), (65.0, 17.5, ATTIC + 0.3), (65.0, 37.0, ATTIC), (64.31, 37.0, ATTIC), (64.31, 37.0, HEAD_IN), (64.167, 37.0, HEAD_IN)]),
    'IU-4': _cu2_attic([(82.4, 20.0, ATTIC), (71.02, 20.0, ATTIC), (71.02, 5.31, ATTIC), (71.02, 5.31, HEAD_IN), (71.02, 5.54, HEAD_IN)]),
    'IU-5': _cu2_out([(83.65, 27.81, LH), (82.98, 27.81, HEAD_IN)]),
    'IU-6': _cu2_out([(83.65, 45.95, LH), (77.7, 45.95, LH), (77.7, 49.5, LH), (77.46, 49.5, HEAD_IN)]),
}
ROUTE_TEXT = {
    'IU-1': 'line-hide to the sleeve by the patio corner, up inside the wall, across the dining and master attics, down the rear wall',
    'IU-2': 'line-hide to the sleeve by the patio corner, up inside the wall, across the dining attic, down the master/dining wall',
    'IU-3': 'line-hide to the sleeve by the patio corner, up inside the wall, along the low edge of the vault into the Bedroom 1 and hall attics, down the living room\'s right wall',
    'IU-4': 'sleeve behind the unit, up inside the wall, across the bedroom-wing attic, down the rear wall',
    'IU-5': 'outside in a line-hide up and along the right wall, straight into the head',
    'IU-6': 'outside in a line-hide along the right wall, around the closet\'s two corners, straight into the head',
}


def head_box(room, side, c):
    """the head's plan rectangle against the room's wall face, and the throw direction"""
    x0, y0, x1, y1 = bbox(ROOMS[room])
    if room == 'master_bed': y0 = 0.46
    if room == 'bed3' and side == 'e': x1 = 77.46
    h = HEAD_W / 2
    if side == 'n': return (c - h, y0, c + h, y0 + HEAD_D), (0, 1), (c, y0)
    if side == 's': return (c - h, y1 - HEAD_D, c + h, y1), (0, -1), (c, y1)
    if side == 'w': return (x0, c - h, x0 + HEAD_D, c + h), (1, 0), (x0, c)
    return (x1 - HEAD_D, c - h, x1, c + h), (-1, 0), (x1, c)


def plen3(pts):
    return sum(math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) for a, b in zip(pts, pts[1:]))


def outside_seg(a, b):
    """an outside line-hide segment: below the attic and not inside the house"""
    if max(a[2], b[2]) >= ATTIC - 0.1: return False
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    r = room_at(mx, my)
    return r is None or r['kind'] == 'outdoor'


def wall_name(side):
    return {'n': 'rear', 's': 'front', 'w': 'left', 'e': 'right'}[side]


def position(room, side, c, wall_face):
    x0, y0, x1, y1 = bbox(ROOMS[room])
    if room == 'master_bed': y0 = 0.46
    if room == 'bed3' and side == 'e': y0 = 45.27
    if side in 'ns': along = f"centred {ft_in(c - x0)} from the left wall"
    else: along = f"centred {ft_in(c - y0)} from the rear wall" if room != 'bed3' else f"centred {ft_in(c - y0)} from the closet wall"
    return f"on the {wall_name(side)} wall, {along}; top at 8'-6\" (6\" below the ceiling)"


def line_size(btu):
    return '1/4" x 3/8"' if btu <= 12000 else '1/4" x 1/2"' if btu <= 18000 else '3/8" x 5/8"'


def unit_rect(u):
    x, y = u['at']
    return (x - CU_D / 2, y - CU_W / 2, x + CU_D / 2, y + CU_W / 2) if u['axis'] == 'x' else (x - CU_W / 2, y - CU_D / 2, x + CU_W / 2, y + CU_D / 2)


def build():
    sh = Sheet('M-1', 'HVAC', 'Ductless: two cold-climate multi-zone mini-split heat pumps with wall heads; the radiant slab (R-1) carries the heat.')
    sh.base()
    loads = {l['id']: l for l in (room_load(r) for r in HEATED)}
    Qh = sum(l['heat'] for l in loads.values()); Qc = sum(l['cool'] for l in loads.values())
    heads, picks, units = [], {}, {}
    for hid, room, side, c, cu, serves, cond, tstat in HEADS:
        cool = sum(loads[r]['cool'] for r in serves) * 1.15        # + latent and a margin
        heat = sum(loads[r]['heat'] for r in serves)
        size = next(s for s in SIZES if s >= cool) if cool <= SIZES[-1] else SIZES[-1]
        if room == 'living': size = max(size, 9000)                 # vault stratification, the open kitchen and cooking
        box_, throw, face = head_box(room, side, c)
        route = ROUTES[hid]
        heads.append(dict(id=hid, room=room, side=side, c=c, cu=cu, serves=serves, cond=cond, tstat=tstat, size=size, cool=cool, heat=heat,
                          box=box_, throw=throw, face=face, route=route, length=plen3(route), line=line_size(size),
                          outside=sum(plen3([a, b]) for a, b in zip(route, route[1:]) if outside_seg(a, b))))
    for cu, u in UNITS.items():
        hs = [h for h in heads if h['cu'] == cu]
        conn = sum(h['size'] for h in hs)
        block = sum(h['cool'] for h in hs) * 0.9                    # the rooms don't all peak at once
        nominal = max(MULTI[max(2, len(hs))], next(n for n in sorted(set(MULTI.values())) if n * 1.3 >= conn))
        units[cu] = dict(u, id=cu, heads=hs, conn=conn, block=block, nominal=nominal, ports=max(2, len(hs)),
                         total=sum(h['length'] for h in hs), longest=max(h['length'] for h in hs))

    # served rooms, tinted by unit
    for h in heads:
        for rid in h['serves']:
            pts = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in ROOMS[rid]['poly'])
            sh.add(f'<polygon points="{pts}" fill="{ZONE[h["cu"]]}" fill-opacity="{0.22 if rid == h["room"] else 0.1}"/>', 'rooms')
    # line sets: outside line-hide runs drawn as a double line, attic and in-wall runs as a single line
    for h in heads:
        r = h['route']
        for a, b in zip(r, r[1:]):
            if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6: continue     # a vertical
            if outside_seg(a, b):
                sh.path([a[:2], b[:2]], LS, 3.2); sh.path([a[:2], b[:2]], '#fff', 1.2)
            else:
                sh.path([a[:2], b[:2]], LS, 1.6)
        for p in r:
            if abs(p[2] - 1.5) < 1e-6 and room_at(*p[:2]) is None: sh.circle(p[0], p[1], 0.35, '#fff', LS, 1.2)   # sleeve through the wall
    # condensate
    for h in heads:
        (bx0, by0, bx1, by1), (tx, ty), (fx, fy) = h['box'], h['throw'], h['face']
        if h['cond'] == 'gravity':
            sh.line(fx, fy, fx - tx * 1.4, fy - ty * 1.4, CD, 1.1, '3,2')
            sh.rect(fx - tx * 1.4 - 0.3, fy - ty * 1.4 - 0.3, fx - tx * 1.4 + 0.3, fy - ty * 1.4 + 0.3, '#fff', CD, 0.9)
        else:
            mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
            k = HEAD_W / 2 + 0.5
            qx, qy = mx + k * (1 if tx == 0 else 0), my + k * (1 if ty == 0 else 0)
            top = [p for p in h['route'] if p[2] >= ATTIC - 0.1][-1]
            sh.path([(qx, qy), top[:2]], CD, 1.1, '3,2')
            sh.circle(qx, qy, 0.32, '#fff', CD, 0.9)
            sh.text(qx, qy + 0.05, 'P', 5, CD, '700')
    # heads
    for h in heads:
        (bx0, by0, bx1, by1), (tx, ty), (fx, fy) = h['box'], h['throw'], h['face']
        mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
        room = ROOMS[h['room']]
        title = f"{h['id']} · {h['size'] // 1000}k wall head · {room['name']} · {UNITS[h['cu']]['sub'].split(',')[0]} {h['cu']}"
        sh.open_group(h['id'], title, hit=(mx, my, 1.4))
        sh.rect(bx0, by0, bx1, by1, '#fff', ZONE[h['cu']], 1.6)
        sh.rect(bx0, by0, bx1, by1, ZONE[h['cu']], 'none', 0, extra=' fill-opacity="0.35"')
        ax, ay = mx + tx * 0.6, my + ty * 0.6
        sh.path([(ax, ay), (ax + tx * 2.4, ay + ty * 2.4)], ZONE[h['cu']], 1.2, '2,2')
        sh.path([(ax + tx * 2.4 - ty * 0.5 - tx * 0.6, ay + ty * 2.4 - tx * 0.5 - ty * 0.6), (ax + tx * 2.4, ay + ty * 2.4), (ax + tx * 2.4 + ty * 0.5 - tx * 0.6, ay + ty * 2.4 + tx * 0.5 - ty * 0.6)], ZONE[h['cu']], 1.2)
        lx, ly = (mx, my + ty * 4.0) if tx == 0 else (mx + tx * 1.7, my - HEAD_W / 2 - 1.1)
        sh.text(lx, ly - 0.45, h['id'], 7, '#7a3f12' if h['cu'] == 'CU-1' else '#1f4f7a', '700')
        sh.text(lx, ly + 0.55, f"{h['size'] // 1000}k", 6, '#555')
        sh.close_group()
        picks[h['id']] = dict(tag=h['id'], sub=room['name'], fields=[
            ('Head', f"{h['size']:,} Btu/h high-wall head on {h['cu']}"),
            ('Position', position(h['room'], h['side'], h['c'], h['face'])),
            ('Why here', WHY[h['id']]),
            ('Serves', ', '.join(ROOMS[r]['name'] for r in h['serves'])),
            ('Load', f"cool {h['cool']:,.0f} Btu/h (with latent and margin) · heat {h['heat']:,.0f} Btu/h (the radiant slab carries it)"),
            ('Line set', f"{h['line']}, about {h['length']:.0f} ft: {ROUTE_TEXT[h['id']]}"),
            ('Condensate', 'gravity, straight out through the wall behind the head to a splash block' if h['cond'] == 'gravity' else 'mini condensate pump behind the head, discharging with the line set to the outside'),
            ('Controller', f"wired wall controller T{h['id'][-1]} at 48\" by the door"),
        ])
        # wired controller
        x, y = h['tstat']
        tid = 'T' + h['id'][-1]
        sh.open_group(tid, f"Wired controller {tid} for {h['id']}, 48\" AFF", hit=(x, y, 0.8))
        sh.circle(x, y, 0.45, '#fff', EQ, 1.0); sh.text(x, y + 0.05, 'T', 5.5, EQ, '700')
        sh.close_group()
        picks[tid] = dict(tag=tid, sub=room['name'], fields=[('Item', f"Wired wall controller for {h['id']}, 48\" to the top, latch side of the door"), ('Wire', 'low-voltage cable from the head (the head\'s own controller connection; no line voltage)')])
    # outdoor units
    for cu, u in units.items():
        x, y = u['at']; rx0, ry0, rx1, ry1 = unit_rect(u)
        sh.open_group(cu, f"{cu} · {u['nominal'] // 1000}k {u['ports']}-port outdoor unit · {u['sub']}", hit=(x, y, 1.8))
        sh.rect(rx0, ry0, rx1, ry1, '#fff', EQ, 1.6)
        sh.circle(x, y, 0.45, 'none', EQ, 0.8)
        sh.close_group()
        if u['axis'] == 'y':
            sh.text(x, ry0 - 2.0, cu, 7.5, EQ, '700'); sh.text(x, ry0 - 1.0, f"{u['nominal'] // 1000}k · {u['ports']} ports", 6, '#555')
        else:
            sh.text(x, ry1 + 1.0, cu, 7.5, EQ, '700'); sh.text(x, ry1 + 2.0, f"{u['nominal'] // 1000}k · {u['ports']} ports", 6, '#555')
        dx, dy, along = u['ds']
        did = 'DS' + cu[-1]
        sh.open_group(did, f"Disconnect {did} for {cu}", hit=(dx, dy, 0.7))
        sh.rect(dx - 0.3, dy - 0.3, dx + 0.3, dy + 0.3, '#fff', EQ, 1.0)
        sh.close_group()
        picks[did] = dict(tag=did, sub=u['sub'], fields=[('Item', f'240 V fused disconnect for {cu}, on the wall within sight of the unit'), ('Circuit', 'dedicated 240 V circuit sized to the unit\'s nameplate MCA/MOCP (E-1)')])
        heat5 = u['nominal'] * AT_5F; heatd = u['nominal'] * AT_DESIGN
        picks[cu] = dict(tag=cu, sub=u['sub'], fields=[
            ('Equipment', f"{u['nominal']:,} Btu/h ({u['nominal'] / 12000:g}-ton) {u['ports']}-port cold-climate multi-zone heat pump (Mitsubishi Hyper-Heat or Fujitsu XLTH class, or equal)"),
            ('Heads', ', '.join(f"{h['id']} {h['size'] // 1000}k" for h in u['heads']) + f" = {u['conn']:,} Btu/h connected ({u['conn'] / u['nominal'] * 100:.0f} % of the unit)"),
            ('Cooling', f"{u['block']:,.0f} Btu/h block load on the rooms it serves"),
            ('Heat', f"about {heat5:,.0f} Btu/h at 5 °F and {heatd:,.0f} Btu/h at {CLIMATE['heat_design_f']:.0f} °F: backup and quick warm-up on top of the radiant slab"),
            ('Why here', u['why']),
            ('Mounting', f'on a concrete pad, raised {u["stand"] * 12:.0f}" on a stand for snow, its back {OFF * 12:.0f}" off the wall (outside the eave drip line, room to service it); snow guards on the roof above; keep 24" in front clear'),
            ('Line sets', f"{len(u['heads'])} sets, {u['total']:.0f} ft in all, longest {u['longest']:.0f} ft (check the model's per-head and total limits)"),
        ])
    sh.legend([
        (f'<line x1="-9" y1="0" x2="9" y2="0" stroke="{LS}" stroke-width="1.6"/>', 'line set LS#, in the attic or inside a wall'),
        (f'<line x1="-9" y1="0" x2="9" y2="0" stroke="{LS}" stroke-width="3.2"/><line x1="-9" y1="0" x2="9" y2="0" stroke="#fff" stroke-width="1.2"/>', 'line set outside, in a line-hide'),
        (f'<circle r="3.5" fill="#fff" stroke="{LS}" stroke-width="1.2"/>', 'sleeve through the wall'),
        (f'<line x1="-9" y1="0" x2="9" y2="0" stroke="{CD}" stroke-width="1.2" stroke-dasharray="3,2"/>', 'condensate'),
        (f'<rect x="-9" y="-3" width="18" height="6" fill="{ZONE["CU-1"]}" fill-opacity="0.5" stroke="{ZONE["CU-1"]}" stroke-width="1.4"/>', 'wall head on CU-1 IU#'),
        (f'<rect x="-9" y="-3" width="18" height="6" fill="{ZONE["CU-2"]}" fill-opacity="0.5" stroke="{ZONE["CU-2"]}" stroke-width="1.4"/>', 'wall head on CU-2 IU#'),
        (f'<rect x="-4" y="-8" width="8" height="16" fill="#fff" stroke="{EQ}" stroke-width="1.4"/><circle r="2.6" fill="none" stroke="{EQ}" stroke-width="0.8"/>', 'outdoor unit CU#'),
        (f'<circle r="3.5" fill="#fff" stroke="{CD}" stroke-width="0.9"/><text y="0.5" font-size="5" font-weight="700" fill="{CD}" text-anchor="middle" dominant-baseline="middle">P</text>', 'condensate pump'),
        (f'<circle r="5" fill="#fff" stroke="{EQ}" stroke-width="1"/><text y="0.5" font-size="5.5" font-weight="700" fill="{EQ}" text-anchor="middle" dominant-baseline="middle">T</text>', 'wired controller T#, 48"'),
        (f'<rect x="-3.3" y="-3.3" width="6.6" height="6.6" fill="#fff" stroke="{EQ}" stroke-width="1"/>', 'disconnect DS#'),
    ])
    sh.title_block(['Heads tinted by unit: CU-1 orange, CU-2 blue; shaded rooms are what each head serves.',
                    f"CU-1 {units['CU-1']['nominal'] // 1000}k · CU-2 {units['CU-2']['nominal'] // 1000}k · cool {Qc / 1000:,.0f} kBtu/h"])

    head_rows = [(h['id'], [h['id'], ROOMS[h['room']]['name'], h['cu'], f"{h['size'] // 1000}k", position(h['room'], h['side'], h['c'], h['face']),
                            f"{h['cool']:,.0f}", f"{h['line']} · {h['length']:.0f} ft", 'gravity' if h['cond'] == 'gravity' else 'pump',
                            ', '.join(ROOMS[r]['name'] for r in h['serves'])]) for h in heads]
    unit_rows = [(cu, [cu, u['sub'], f"{u['nominal'] // 1000}k, {u['ports']} ports", f"{u['conn'] // 1000}k ({u['conn'] / u['nominal'] * 100:.0f} %)",
                       f"{u['block']:,.0f}", f"{u['nominal'] * AT_5F:,.0f} / {u['nominal'] * AT_DESIGN:,.0f}", f"{u['total']:.0f} ft, longest {u['longest']:.0f}"]) for cu, u in units.items()]
    served = {r: h for h in heads for r in h['serves']}
    rows = [(served[l['id']]['id'] if l['id'] in served else None,
             [l['name'], f"{l['area']:,.0f}", f"{l['heat']:,.0f}", f"{l['cool']:,.0f}", served[l['id']]['id'] if l['id'] in served else '— (spill from next room)']) for l in loads.values()]
    ls_rows = [(None, ['LS-' + h['id'][-1], f"{h['cu']} → {h['id']}", h['line'], f"{h['length']:.0f} ft", f"{h['outside']:.0f} ft", ROUTE_TEXT[h['id']]]) for h in heads]
    lf = sum(h['length'] for h in heads)
    pumps = sum(1 for h in heads if h['cond'] == 'pump')
    sleeves = sum(1 for h in heads if h['cond'] == 'gravity') + 2
    total_rows = [
        (None, ['Heating load', f'{Qh:,.0f} Btu/h', f"{CLIMATE['indoor_heat_f']}°F inside, {CLIMATE['heat_design_f']}°F outside; carried by the radiant slab (R-1)"]),
        (None, ['Cooling load', f'{Qc:,.0f} Btu/h sensible', f"{CLIMATE['indoor_cool_f']}°F inside, {CLIMATE['cool_design_f']}°F outside"]),
        (None, ['Outdoor units', f"CU-1 {units['CU-1']['nominal'] // 1000}k + CU-2 {units['CU-2']['nominal'] // 1000}k", 'cold-climate multi-zone, sized on cooling and the head count']),
        (None, ['Mini-split heat', f"{sum(u['nominal'] for u in units.values()) * AT_DESIGN:,.0f} Btu/h at {CLIMATE['heat_design_f']:.0f}°F", 'backup to the slab in the rooms with heads']),
        (None, ['Indoor heads', str(len(heads)), 'high-wall, 6" below the ceiling']),
        (None, ['Line sets', f'{lf:.0f} ft', f"longest {max(h['length'] for h in heads):.0f} ft; {sum(h['outside'] for h in heads):.0f} ft of it outside in line-hide"]),
    ]
    notes = [
        f"Design conditions: {CLIMATE['name']} ({CLIMATE['source']}). Heating {CLIMATE['heat_design_f']}°F, cooling {CLIMATE['cool_design_f']}°F; inside {CLIMATE['indoor_heat_f']}°F / {CLIMATE['indoor_cool_f']}°F.",
        'No ducts. The radiant slab (R-1) heats every room; the mini-splits cool the rooms with heads and give fast, second-source heat there. Rooms without a head (office, laundry, mud room, powder, halls) take air from the next room through their doors.',
        'Sizing: each head carries the cooling load of the rooms it serves plus 15 % for latent and margin, with 6k the smallest head; the living head is held at 9k for the vault, the open kitchen and cooking. Each outdoor unit is the smallest common cold-climate multi-zone with enough ports, with the heads at no more than 130 % of its rating.',
        'Outdoor units sit on a concrete pad against an exterior wall, raised 12" on a stand for snow, backs 30" off the wall so they are outside the eave drip line and can be serviced; snow guards on the roof above each. CU-1 is in the rear alcove between the master bedroom and the patio; CU-2 is on the Bath 2 wall of the bedroom wing. Line sets were routed for the shortest run from there.',
        'Line sets to heads on exterior walls stay outside: from the unit in a painted line-hide along the wall at about 8\' (just above the window heads) and straight through the wall into the back of the head (IU-5, IU-6). The others go through a sealed sleeve about 18" up, rise inside a full-height stud bay to the attic, run on the ceiling framing under the insulation and drop inside the wall behind the head. The living set rides the low edge of the kitchen/living vault at Y 17\'-6", where the scissor trusses\' bottom chord is only about 6" above the plate, then the Bedroom 1 and hall attics; nothing crosses the middle of the vault.',
        'Heads mount high on the wall, top 6" below the ceiling, on a wall that lets them throw across the room. Exterior-wall heads drain condensate by gravity straight out the wall to a splash block (with the line set where there is one); interior-wall heads (IU-2, IU-3) get a mini condensate pump behind the head that discharges outside with the line set.',
        'Pressure test, evacuate and pull a micron vacuum per the maker. Every sleeve is sealed and flashed; line-hide painted to the siding.',
        'Each outdoor unit has a dedicated 240 V circuit and a fused disconnect on the wall within sight (DS1 on the master bedroom\'s alcove wall, DS2 beside CU-2 on the Bath 2 wall), sized to the nameplate MCA/MOCP once the units are picked (E-1). The heads are powered from their outdoor unit through the 14/4 interconnect run with the line set.',
        'Wired wall controllers T1-T6 at 48" by each door; set the heads to cool and to heat only below the slab\'s setpoint so they don\'t fight the radiant.',
        'Ventilation: with no ducts, the draft assumes continuous low-speed bath fans (exhaust-only, E-1) for the IRC whole-house rate; paired through-wall ERVs are the upgrade (see open items).',
    ]
    open_items = [
        'CU-1 in the rear alcove: it is 2 ft from the edge of the covered patio and under the dining windows, so it is heard on the patio and in the dining room when it runs. The alternatives are the master bedroom\'s left wall (quiet, but the living set runs about 105 ft, past the per-head limit) or the front porch (every set under 75 ft, in sight of the street).',
        'CU-2 on the Bath 2 wall: 3 ft from Bedroom 2\'s window W14. The Bath 1 wall is the quiet spot (8 ft from any bedroom window) for about 10 ft more line.',
        f"Exact models: pick the brand, then confirm the heads are an allowed combination and the line lengths are inside the unit's limits (CU-1: longest {units['CU-1']['longest']:.0f} ft, total {units['CU-1']['total']:.0f} ft; CU-2: longest {units['CU-2']['longest']:.0f} ft, total {units['CU-2']['total']:.0f} ft).",
        'Truss maker: the living set crosses the scissor trusses at Y 17\'-6"; leave web openings for a 2" bundle there, or run it along a truss.',
        'Office: no head as drawn (the ask was the right-side bedrooms). A 6k head on the office\'s right wall would make CU-2 a 4-port.',
        'Bed walls: the master and Bedroom 1 heads sit on the rear wall between the windows, where a headboard may go. A head over a headboard works with its vanes set level; otherwise it moves to a side wall. Confirm furniture walls before rough-in.',
        f"Ventilation: continuous bath fans (drawn) or paired through-wall ERVs (about {0.03 * HOUSE['totals']['heated_gross_sf'] + 7.5 * 5:.0f} CFM continuous under the IRC).",
    ]
    tables = [
        dict(key='heads', title='Indoor heads', cols=['Tag', 'Room', 'Unit', 'Size', 'Position', 'Cool Btu/h', 'Line set', 'Condensate', 'Serves'], rows=head_rows),
        dict(key='units', title='Outdoor units', cols=['Tag', 'Location', 'Size', 'Heads connected', 'Cool block Btu/h', 'Heat at 5°F / design', 'Line sets'], rows=unit_rows),
        dict(key='ls', title='Line sets', cols=['Set', 'Run', 'Size', 'Length', 'Outside', 'Route'], rows=ls_rows),
        dict(key='rooms', title='Room loads', cols=['Room', 'Floor sf', 'Heat Btu/h', 'Cool Btu/h', 'Head'], rows=rows),
        dict(key='system', title='System', cols=['Item', 'Size', 'Basis'], rows=total_rows),
        dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the layout, for pricing. The HVAC contractor takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=[
            (None, [f"Outdoor unit, {units['CU-1']['nominal'] // 1000}k {units['CU-1']['ports']}-port", '1', 'CU-1, cold-climate multi-zone']),
            (None, [f"Outdoor unit, {units['CU-2']['nominal'] // 1000}k {units['CU-2']['ports']}-port", '1', 'CU-2, cold-climate multi-zone']),
        ] + [(None, [f'Wall head, {s // 1000}k', str(n), '']) for s, n in sorted({h['size']: sum(1 for g in heads if g['size'] == h['size']) for h in heads}.items())] + [
            (None, ['Line set, insulated', f'{lf * 1.1:.0f} ft', 'all sets + 10 %; sizes per the line-set table']),
            (None, ['Interconnect cable 14/4', f'{lf * 1.1:.0f} ft', 'with the line sets']),
            (None, ['Line-hide cover', f"{sum(h['outside'] for h in heads) * 1.1:.0f} ft", 'painted to the siding']),
            (None, ['Wall sleeves', str(sleeves), 'sealed and flashed']),
            (None, ['Condensate pump', str(pumps), 'IU-2, IU-3']),
            (None, ['Wired wall controller', str(len(heads)), 'T1-T6']),
            (None, ['Pad, stand, snow guards', '2', '12" stands on pads']),
            (None, ['Disconnect', '2', 'DS1, DS2; circuits on E-1']),
        ]),
    ]
    tons = sum(u['nominal'] for u in units.values()) / 12000
    summary = dict(heat=round(Qh), cool=round(Qc), tons=tons, units=len(units), heads=len(heads), backup_kw=0)
    for l in loads.values():
        l['cfm'] = l['cool'] / (1.08 * 20)       # air a head must move to cool the room at a 20 °F split
    hv3d = dict(units=[], heads=[], lines=[], parts=[])
    for cu, u in units.items():
        rx0, ry0, rx1, ry1 = unit_rect(u); st = u['stand']
        hv3d['units'].append(dict(x0=rx0, y0=ry0, x1=rx1, y1=ry1, stand=st, top=st + CU_H,
                                  name=f"{cu} · {u['nominal'] // 1000}k {u['ports']}-port outdoor unit",
                                  text=f"{u['sub']}. Heads: " + ', '.join(f"{h['id']} {h['size'] // 1000}k" for h in u['heads']) + f'. On a pad, {st * 12:.0f}" stand, back {OFF * 12:.0f}" off the wall.'))
        dx, dy, along = u['ds']
        w = (0.1, 0.3) if along == 'x' else (0.3, 0.1)
        hv3d['parts'].append(dict(x0=dx - w[0], y0=dy - w[1], x1=dx + w[0], y1=dy + w[1], b=4.0, t=5.0, name=f"DS{cu[-1]} · disconnect for {cu}", text='240 V fused disconnect within sight of the unit (E-1)'))
    for h in heads:
        (bx0, by0, bx1, by1) = h['box']
        hv3d['heads'].append(dict(x0=bx0, y0=by0, x1=bx1, y1=by1, b=HEAD_TOP - HEAD_H, t=HEAD_TOP, name=f"{h['id']} · {h['size'] // 1000}k wall head ({h['cu']})",
                                  text=f"{ROOMS[h['room']]['name']}: {position(h['room'], h['side'], h['c'], h['face'])}. Condensate: {'gravity out the wall' if h['cond'] == 'gravity' else 'pump'}."))
        k = [g['id'] for g in units[h['cu']]['heads']].index(h['id']); off = (k - (len(units[h['cu']]['heads']) - 1) / 2) * 0.22
        pts = [[x + off, y + off, z] for x, y, z in h['route']]
        hv3d['lines'].append(dict(kind='ls', name=f"LS-{h['id'][-1]} · line set to {h['id']}", text=f"{h['line']}, about {h['length']:.0f} ft: {ROUTE_TEXT[h['id']]}", pts=pts))
        (fx, fy), (tx, ty) = h['face'], h['throw']
        if h['cond'] == 'gravity':
            hv3d['lines'].append(dict(kind='cd', name=f"Condensate from {h['id']}", text='gravity, out through the wall to a splash block',
                                      pts=[[fx + tx * 0.2, fy + ty * 0.2, HEAD_TOP - HEAD_H + 0.1], [fx - tx * 0.6, fy - ty * 0.6, HEAD_TOP - HEAD_H - 0.1], [fx - tx * 0.6, fy - ty * 0.6, 0.2]]))
        x, y = h['tstat']
        hv3d['parts'].append(dict(x0=x - 0.2, y0=y - 0.2, x1=x + 0.2, y1=y + 0.2, b=3.75, t=4.0, name=f"T{h['id'][-1]} · wired controller for {h['id']}", text='48" to the top, by the door'))
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, loads=list(loads.values()), hvac3d=hv3d,
                legend=[(LS, 'refrigerant line sets LS#: double line outside in line-hide, single in the attic or a wall'), (CD, 'condensate (P = pump)'),
                        (ZONE['CU-1'], 'CU-1 heads and the rooms they serve'), (ZONE['CU-2'], 'CU-2 heads and the rooms they serve'), (EQ, 'outdoor units, disconnects DS#, controllers T#')])


if __name__ == '__main__':
    b = build()
    print(b['summary'])
    for r in b['tables'][2]['rows'] + b['tables'][1]['rows']: print(r[1])
