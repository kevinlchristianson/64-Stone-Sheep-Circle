"""P-1 Plumbing: fixture schedule, drain/vent stacks, under-slab drain routing and PEX supply.

Fixtures and drains are A-5's (plan/house.json). Everything else is a first
draft for the plumber: a slab-on-grade house (the garage and mechanical floor
drains point that way) with a 4" building drain leaving under the front
porch, five fixture groups each on its own 3" stack through the roof, an
island vent at the kitchen sink, and a PEX home-run manifold with the water
heater in the mechanical closet. Drainage fixture units and supply fixture
units from the IPC (Tables 709.1 and E103.3).
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
MANIFOLD = (32.4, 46.4)
WATER_HEATER = (32.4, 51.0)
EXIT = (33.0, 53.7)   # building drain leaves under the front wall, through the porch to the street (assumed)

STACKS = [
    dict(id='ST1', name='Master bath', at=(10.0, 16.8), fixtures=['MB-WC', 'MB-TUB', 'MB-LAV1', 'MB-LAV2', 'MB-SHR', 'MB-FD'],
         route=[(10.0, 16.8), (10.0, 24.6), (12.0, 24.6), (12.0, 35.5), (31.6, 35.5)]),
    dict(id='ST2', name='Laundry and powder', at=(24.5, 25.0), fixtures=['LA-WASH', 'PR-WC', 'PR-LAV'],
         route=[(24.5, 25.0), (24.5, 35.5)]),
    dict(id='ST3', name='Kitchen island (island vent)', at=(38.68, 28.6), fixtures=['K-SINK', 'K-DW'],
         route=[(38.68, 28.6), (38.68, 36.6), (35.0, 36.6), (35.0, 44.0), (33.0, 44.0)]),
    dict(id='ST4', name='Bath 1', at=(79.6, 12.4), fixtures=['B1-WC', 'B1-LAV', 'B1-SHR', 'B1-FD'],
         route=[(79.6, 12.4), (79.6, 46.6), (45.0, 46.6), (45.0, 44.0), (35.0, 44.0)]),
    dict(id='ST5', name='Bath 2', at=(78.6, 37.0), fixtures=['B2-WC', 'B2-LAV1', 'B2-LAV2', 'B2-TUB'],
         route=[(78.6, 37.0), (79.6, 37.0)]),
]
MAIN = [(31.6, 35.5), (31.6, 44.0), (33.0, 44.0), EXIT, (33.0, 62.8)]
FLOOR_DRAINS = [dict(id='GA-FD', route=[(14.96, 52.14), (30.0, 52.14), (33.0, 52.14)]),
                dict(id='ME-FD', route=[(32.02, 49.23), (33.0, 49.23)])]
HOSE = [dict(id='HB1', at=(36.0, 53.9), name='Hose bibb, front porch (frost-free)'),
        dict(id='HB2', at=(46.0, 16.6), name='Hose bibb, rear patio (frost-free)'),
        dict(id='HB3', at=(0.5, 44.0), name='Hose bibb, garage door wall (frost-free)')]


def plen(pts): return sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def manhattan(a, b, first='x'):
    return [a, (b[0], a[1]), b] if first == 'x' else [a, (a[0], b[1]), b]


# ---------------------------------------------------------------- vents and the 3D model (Zero Rd's buildPlumbing, for a slab)
CEIL = HOUSE['meta']['ceiling_ft']
DRAIN_H, HOT_H, COLD_H = -1.6, -0.8, -0.6     # under the slab: drains deepest, PEX in the base course above them
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


def arm_of(f, s):
    return manhattan(f['at'], s['at'], 'y' if f['room'] in ('bath1', 'bath2') else 'x')


def arm_size(f):
    return '2"' if f['kind'] in ('shower', 'washer', 'drain') else '3"' if f['kind'] == 'wc' else '1-1/2"'


ISLAND = 'ST3'


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
    sh = Sheet('P-1', 'Plumbing', 'Fixtures from A-5; drain, vent and supply routing is a first draft for the plumber (slab on grade, 4" building drain out the front).')
    sh.base()
    picks, fix_rows = {}, []
    stack_of = {fid: s for s in STACKS for fid in s['fixtures']}
    dfu_total = wsfu_c = wsfu_h = 0
    drain_lf = {'4"': plen(MAIN) + 0, '3"': 0, '2"': 0, '1-1/2"': 0}
    # building drain and stacks
    sh.path(MAIN, DRAIN, 3.2)
    for s in STACKS:
        sh.path(s['route'], DRAIN, 2.4)
        drain_lf['3"'] += plen(s['route'])
    for fd in FLOOR_DRAINS:
        sh.path(fd['route'], DRAIN, 1.8, '6,3')
        drain_lf['2"'] += plen(fd['route'])
    # fixture arms
    for f in PLUMBED:
        s = stack_of.get(f['id'])
        name, dfu, trap, wc, wh, sup = TABLE[f['kind']]
        dfu_total += dfu; wsfu_c += wc; wsfu_h += wh
        if s and f['kind'] != 'dw':
            arm = arm_of(f, s)
            sh.path(arm, DRAIN, 1.3)
            drain_lf[arm_size(f)] += plen(arm)
        # supply home runs from the manifold
        if wc: sh.path(manhattan(MANIFOLD, f['at'], 'y'), COLD, 0.7, '1,0', extra=' opacity="0.55"')
        if wh: sh.path(manhattan((MANIFOLD[0] + 0.3, MANIFOLD[1]), (f['at'][0] + 0.3, f['at'][1] + 0.3), 'y'), HOT, 0.7, extra=' opacity="0.55"')
    # vents: under-slab legs dashed, the riser in the wall a dot, attic runs to the stack thin green
    VENTS = vents()
    vent_lf = 0
    for v in VENTS:
        if v.get('under'): sh.path(v['under'], VENT, 1.0, '4,2'); vent_lf += plen(v['under'])
        if v.get('attic'): sh.path(v['attic'], VENT, 1.0, extra=' opacity="0.8"'); vent_lf += plen(v['attic'])
        sh.circle(*v['wall'], 0.22, VENT, VENT, 0)
        vent_lf += VENT_H
    for i, s in enumerate(STACKS, 1):
        x, y = s['at']
        dfu = sum(TABLE[FIX[fid]['kind']][1] for fid in s['fixtures'])
        title = f"{s['id']} · {s['name']} stack, {dfu} DFU"
        sh.open_group(s['id'], title, hit=(x, y, 0.9))
        sh.circle(x, y, 0.55, '#fff', VENT, 2.0); sh.circle(x, y, 0.22, VENT, VENT, 0)
        sh.close_group()
        sh.text(x + 1.4, y - 0.9, s['id'], 7, VENT, '700')
        vent = '3" vent through the roof' if s['id'] != 'ST3' else 'island loop vent or AAV (where allowed), 2"'
        picks[s['id']] = dict(tag=s['id'], sub=s['name'], fields=[('Fixtures', ', '.join(f"{FIX[fid]['name']} ({fid})" for fid in s['fixtures'])),
                                                               ('Drainage', f'{dfu} DFU on a 3" branch at 1/4" per ft'), ('Vent', vent), ('Route', f"{plen(s['route']):.0f} ft of 3\" under the slab to the 4\" building drain")])
    # fixtures as picks
    for f in PLUMBED:
        name, dfu, trap, wc, wh, sup = TABLE[f['kind']]
        s = stack_of.get(f['id'])
        x, y = f['at']
        title = f"{f['id']} · {f['name']}"
        sh.open_group(f['id'], title, hit=(x, y, 0.9))
        sh.circle(x, y, 0.35, DRAIN if f['kind'] == 'drain' else '#fff', DRAIN, 1.0)
        sh.close_group()
        rm = ROOMS[f['room']]['name']
        fields = [('Fixture', f['name']), ('Room', rm), ('Trap / drain', trap), ('DFU', str(dfu)), ('Supply', f'{sup} PEX home run' + (' (cold and hot)' if wc and wh else ' (hot)' if wh else ' (cold)' if wc else '')),
                  ('Stack', f"{s['id']} {s['name']}" if s else 'floor drain line'), ('Run from manifold', f"~{plen(manhattan(MANIFOLD, f['at'], 'y')):.0f} ft")]
        v = next((v for v in VENTS if v['ref'] == f['id']), None)
        if v: fields.append(('Vent', f"{v['size']} up the {'exterior' if v['ext'] else 'interior'} wall behind it" + (f", across the attic to {v['to']}" if v['to'] else ', through the roof on its own') + (' (loop vent in the island first, then under the slab to the wall)' if v.get('loop') else ' (under the slab to the wall first)' if v.get('under') else '')))
        if f['id'] == 'GA-FD': fields.append(('Code', 'A garage floor drain to the sanitary sewer needs an oil/sand interceptor in most jurisdictions; or drain to daylight'))
        if f['id'] == 'PR-LAV': fields.append(('Note', 'Not drawn on A-5; assumed so the powder room has a sink'))
        picks[f['id']] = dict(tag=f['id'], sub=rm, fields=fields)
        fix_rows.append((f['id'], [f['id'], f['name'], rm, trap, str(dfu), sup if f['kind'] != 'drain' else '—', s['id'] if s else 'FD line']))
    for h in HOSE:
        x, y = h['at']
        sh.open_group(h['id'], h['name'], hit=(x, y, 0.8)); sh.rect(x - 0.3, y - 0.3, x + 0.3, y + 0.3, COLD, COLD, 0); sh.close_group()
        sh.path(manhattan(MANIFOLD, h['at'], 'y'), COLD, 0.7, extra=' opacity="0.55"')
        wsfu_c += 2.5
        picks[h['id']] = dict(tag=h['id'], sub='Hose bibb', fields=[('Fixture', h['name']), ('Supply', '3/4" PEX, frost-free sillcock with vacuum breaker')])
        fix_rows.append((h['id'], [h['id'], h['name'], 'Outside', '—', '—', '3/4"', '—']))
    # manifold, water heater, cleanouts
    for id, at, name, color in [('MAN', MANIFOLD, 'PEX manifold and main shutoff (water service enters here)', COLD), ('WH', WATER_HEATER, 'Water heater, 50 gal (heat-pump or gas, confirm)', HOT)]:
        x, y = at
        sh.open_group(id, name, hit=(x, y, 0.9)); sh.rect(x - 0.6, y - 0.6, x + 0.6, y + 0.6, '#fff', color, 1.6); sh.text(x, y, id, 5.5, color, '700'); sh.close_group()
    picks['MAN'] = dict(tag='MAN', sub='Mechanical closet', fields=[('Item', 'PEX home-run manifold, 1" trunk, with the main shutoff and PRV if street pressure is over 80 psi'),
                                                                  ('Service', '1" water service, entry location not on the site plan'), ('Load', f'{wsfu_c + wsfu_h:.1f} WSFU total')])
    picks['WH'] = dict(tag='WH', sub='Mechanical closet', fields=[('Item', '50 gal water heater on a drain pan to the floor drain; expansion tank; T&P to the floor drain'),
                                                               ('Sizing', 'two tubs and two showers: 50 gal heat-pump (≥ 65 gal first-hour) or gas; a heat-pump unit needs ~700 cu ft of air or ducting, which this 3\' x 8\' closet lacks — see open items')])
    for id, at in [('CO1', (33.0, 53.0)), ('CO2', (31.6, 35.5)), ('CO3', (79.6, 46.6))]:
        x, y = at
        sh.open_group(id, 'Cleanout', hit=(x, y, 0.7)); sh.circle(x, y, 0.3, '#fff', DRAIN, 1.4); sh.text(x + 0.9, y + 0.7, id, 5.5, DRAIN, '700'); sh.close_group()
        picks[id] = dict(tag=id, sub='Cleanout', fields=[('Item', '4" cleanout to grade or floor' if id == 'CO1' else '3" cleanout at a change of direction')])
    sh.text(EXIT[0] + 0.6, 61.6, '4" building drain to sewer / septic (location TBD)', 6.5, DRAIN, '600', anchor='start')

    supply_gpm = round(0.5 * (wsfu_c + wsfu_h) ** 0.75 + 4, 1)  # rough Hunter curve fit for small counts
    notes = [
        'Slab on grade assumed (A-5 shows floor drains in the garage and mechanical closet). All drains and supply runs are under the slab or in walls; no attic plumbing.',
        f'Building drain 4" at 1/4" per ft, {dfu_total} DFU total ({dfu_total} of 216 allowed on 4"). Five fixture groups, each on a 3" stack with a 3" vent through the roof; the kitchen island on a loop vent or an air admittance valve where the AHJ allows.',
        f'Supply: 1" service to a PEX home-run manifold in the mechanical closet; {wsfu_c:.1f} cold + {wsfu_h:.1f} hot WSFU. 1/2" PEX to each fixture, 3/4" to hose bibbs. Pressure-balanced or thermostatic valves at the tubs and showers.',
        'Wet walls framed 2x6 (see S-1). ADA toilets as drawn: 17-19" bowl height, grab-bar blocking.',
        'Water heater in the mechanical closet with a pan and the T&P and pan drain to the closet floor drain.',
    ]
    open_items = [
        'Where the house connects: city sewer or septic, and which side of the lot. The drain is drawn leaving under the front porch.',
        'Water source (city or well) and where it enters; the manifold is drawn in the mechanical closet.',
        'Water heater fuel and type. A heat-pump water heater needs about 700 cu ft of air or a ducted kit; the 3\' x 8\' mechanical closet is too small without one. A gas unit needs venting and combustion air.',
        'Powder room sink is not drawn on A-5 (one is shown here, assumed).',
        'Garage floor drain: sanitary with an interceptor, or to daylight (lot grading).',
        'Kitchen island vent method (loop vent vs. AAV) depends on the local code.',
        'Fixture models: A-5 tags the drains K-9135 and K-9136; tub, toilet, faucet and valve models still to pick.',
    ]
    sh.title_block(['Drains black (4" main heavy), floor-drain lines dashed, stacks green.', 'Vents green: a dot where each rises in the wall, thin line across the attic to its stack, dashed where it runs under the slab.', 'PEX supply home runs: cold blue, hot red.', 'Routing is schematic: the plumber lays out the final runs.'])
    tables = [
        dict(key='fixtures', title='Fixture schedule', cols=['Tag', 'Fixture', 'Room', 'Trap / drain', 'DFU', 'Supply', 'Stack'], rows=fix_rows),
        dict(key='stacks', title='Stacks and vents', cols=['Stack', 'Group', 'Fixtures', 'DFU', 'Vent'],
             rows=[(s['id'], [s['id'], s['name'], str(len(s['fixtures'])), str(sum(TABLE[FIX[f]['kind']][1] for f in s['fixtures'])), '3" VTR' if s['id'] != 'ST3' else 'loop vent / AAV']) for s in STACKS]),
        dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the routing above, for pricing. The plumber takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=[
            (None, ['4" PVC DWV', f"{drain_lf['4\"'] * 1.15:.0f} ft", 'building drain to the front wall + 10 ft to the property line stub (more to the sewer/septic)']),
            (None, ['3" PVC DWV', f"{drain_lf['3\"'] * 1.15:.0f} ft", 'branches and toilet arms, + 15 %; plus ~50 ft for the four 3" vent stacks']),
            (None, ['2" PVC DWV', f"{drain_lf['2\"'] * 1.15 + 40:.0f} ft", 'showers, washer, floor drains, + vents']),
            (None, ['1-1/2" PVC DWV', f"{drain_lf['1-1/2\"'] * 1.15 + 40:.0f} ft", 'lavs, tubs, kitchen sink, + vents']),
            (None, ['1/2" PEX', f"{sum(plen(manhattan(MANIFOLD, f['at'], 'y')) * ((1 if TABLE[f['kind']][3] else 0) + (1 if TABLE[f['kind']][4] else 0)) for f in PLUMBED) * 1.2:.0f} ft", 'home runs cold + hot, + 20 %']),
            (None, ['3/4" PEX', f"{sum(plen(manhattan(MANIFOLD, h['at'], 'y')) for h in HOSE) * 1.2:.0f} ft", 'hose bibbs']),
            (None, ['PEX manifold', '1', f"{sum(1 for f in PLUMBED if TABLE[f['kind']][3]) + len(HOSE)} cold + {sum(1 for f in PLUMBED if TABLE[f['kind']][4])} hot ports"]),
            (None, ['Water heater', '1', '50 gal, pan, expansion tank']),
            (None, ['Toilets', str(sum(1 for f in PLUMBED if f['kind'] == 'wc')), 'ADA height (A-5)']),
            (None, ['Tub/shower valves', str(sum(1 for f in PLUMBED if f['kind'] in ('tub', 'shower'))), 'pressure-balanced']),
            (None, ['Shower drains', '2', 'K-9136 (master), K-9135 (bath 1) per A-5']),
            (None, ['Floor drains', '2', 'garage and mechanical, K-9136 per A-5']),
            (None, ['Cleanouts', '3', '4" at the exit, 3" at changes of direction']),
            (None, ['Hose bibbs', str(len(HOSE)), 'frost-free']),
        ]),
    ]
    summary = dict(fixtures=len(PLUMBED), dfu=dfu_total, wsfu=round(wsfu_c + wsfu_h, 1), stacks=len(STACKS), peak_gpm=supply_gpm)
    lines = [dict(name='4" building drain', pts=MAIN, r=0.17)] + [dict(name=f"{s['id']} {s['name']} branch, 3\"", pts=s['route'], r=0.13) for s in STACKS] + [dict(name='Floor drain line, 2"', pts=fd['route'], r=0.09) for fd in FLOOR_DRAINS]
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, lines=lines, stacks=STACKS, hose=HOSE, plumb3d=model3d(VENTS, wsfu_c + wsfu_h))


def model3d(VENTS, wsfu):
    """The P-1 layer for the 3D model, the way Zero Rd draws it: pipes as tubes at their real depth. Drains under the slab
    with a riser up to each fixture, stacks up through the roof, vents up the walls and across the attic, cold and hot PEX
    home runs under the slab from the manifold with risers to each fixture. Each part is {m, r, pts: [[x, y, h], ...]} or
    a {shape} block, with the name/ref/text a pick shows; ref is the P-1 tag so 3D comments land on the same item."""
    out = []
    def tube(m, r, pts, ref, name, text): out.append(dict(m=m, r=r, pts=[[round(x, 2), round(y, 2), round(h, 2)] for x, y, h in pts], ref=ref, name=name, text=text))
    flat = lambda pts, h: [(x, y, h) for x, y in pts]
    stack_of = {fid: s for s in STACKS for fid in s['fixtures']}
    # drains
    tube('drain', SIZE_R['4"'], flat(MAIN, DRAIN_H), 'CO1', '4" building drain', 'Under the slab at 1/4" per ft, out under the front porch to the sewer or septic (P-1)')
    for s in STACKS:
        tube('drain', SIZE_R['3"'], flat(s['route'], DRAIN_H), s['id'], f"{s['id']} · {s['name']} branch", f'3" under the slab to the 4" building drain, {plen(s["route"]):.0f} ft')
    for fd in FLOOR_DRAINS:
        tube('drain', SIZE_R['2"'], flat(fd['route'], DRAIN_H), fd['id'], f"{fd['id']} · floor drain line", '2" under the slab to the building drain')
    for f in PLUMBED:
        s = stack_of.get(f['id']); name = f"{f['id']} · {f['name']}"
        if s and f['kind'] != 'dw':
            tube('drain', SIZE_R[arm_size(f)], flat(arm_of(f, s), DRAIN_H), f['id'], name, f"{arm_size(f)} fixture drain under the slab to {s['id']}")
        if f['kind'] in ('dw', 'shower'): continue      # dishwasher through the sink tailpiece; a shower drains through its floor drain
        top = {'wc': 0.15, 'drain': 0.0, 'tub': 0.3, 'washer': 2.8}.get(f['kind'], 1.4)
        tube('drain', 0.15 if f['kind'] == 'wc' else SIZE_R[arm_size(f)], [(*f['at'], DRAIN_H), (*f['at'], top)], f['id'], name, f"{TABLE[f['kind']][2]} drain up through the slab to the trap")
    # stacks through the roof (the island has a loop vent instead)
    for s in STACKS:
        if s['id'] == ISLAND: continue
        x, y = s['at']
        tube('vent', 0.13, [(x, y, DRAIN_H), (x, y, roof_over(s['at']) + 1.0)], s['id'], f"{s['id']} · {s['name']} stack", '3" stack: drains at the base under the slab, up the wall and through the roof as the vent')
    # fixture vents
    for v in VENTS:
        f, r, (wx, wy) = v['fixture'], SIZE_R[v['size']] * 0.8, v['wall']
        name, text = f"{f['id']} · {f['name']} vent", f"{v['size']} vent" + (f", to the {v['to']} stack in the attic" if v['to'] else ' through the roof')
        if v.get('loop'):
            x, y = f['at']
            tube('vent', r, [(x + 0.3, y, DRAIN_H + 0.3), (x + 0.3, y, 2.6), (x + 0.6, y + 0.3, 2.6), (x + 0.6, y + 0.3, DRAIN_H + 0.3)], f['id'], f"{f['id']} · island loop vent", 'Loop vent: rises inside the island to the counter underside and loops back down (or an AAV where the AHJ allows)')
            tube('vent', r, flat([(x + 0.6, y + 0.3)] + v['under'][1:], DRAIN_H + 0.3), f['id'], name, f'2" vent under the slab to the laundry wall, then up to ST2\'s vent in the attic')
            low = DRAIN_H + 0.3
        elif v.get('under'):
            tube('vent', r, flat(v['under'], DRAIN_H + 0.3), f['id'], name, text + '; runs under the slab to the wall first')
            low = DRAIN_H + 0.3
        else:
            low = 0.0 if f['kind'] in ('wc', 'tub', 'shower', 'drain') else 1.3
        top = VENT_H if v['attic'] else roof_over(v['wall']) + 1.0
        tube('vent', r, [(wx, wy, low), (wx, wy, top)], f['id'], name, text + f", rising in the {'exterior' if v['ext'] else 'interior'} wall")
        if v['attic']: tube('vent', r, flat(v['attic'], VENT_H), f['id'], name, text + ', across the attic over the ceiling')
    # supply: 1" service up into the closet, the manifold and the water heater, home runs under the slab
    mx, my = MANIFOLD
    tube('cold', 0.09, [(mx - 0.4, my, -4.5), (mx - 0.4, my, 3.0)], 'MAN', 'Water service, 1"', '1" service up through the slab to the main shutoff and the manifold; it comes in below the frost line (about 4\' in Powell), entry point TBD')
    out.append(dict(shape='box', m='cold', box=[mx - 0.15, my - 1.1, mx + 0.15, my + 1.1, 3.0, 4.2], ref='MAN', name='MAN · PEX manifold', text=f'Home-run manifold and main shutoff, {wsfu:.1f} WSFU; cold and hot ports, each line under the slab to one fixture'))
    wx, wy = WATER_HEATER
    out.append(dict(shape='cyl', m='hot', at=[wx, wy], r=0.95, h=[0.0, 5.0], ref='WH', name='WH · water heater, 50 gal', text='On a pan; T&P and pan drain to the closet floor drain; feeds the hot side of the manifold'))
    tube('hot', 0.06, [(wx, wy - 0.95, 4.6), (mx + 0.4, wy - 0.95, 4.6), (mx + 0.4, my + 1.1, 4.6), (mx + 0.4, my + 1.1, 3.6)], 'WH', 'WH · hot to the manifold', '3/4" hot from the water heater to the hot side of the manifold')
    for f in PLUMBED:
        name, dfu, trap, wc, wh, sup = TABLE[f['kind']]
        x, y = f['at']
        top = {'wc': 0.7, 'tub': 2.4, 'shower': 4.0, 'washer': 3.5, 'dw': 1.0}.get(f['kind'], 1.7)
        if wc:
            run = manhattan(MANIFOLD, f['at'], 'y')
            tube('cold', 0.035, [(mx, my, 3.0), (mx, my, COLD_H)] + flat(run[1:], COLD_H) + [(x, y, top)], f['id'], f"{f['id']} · cold to {f['name'].lower()}", f'{sup} PEX cold home run under the slab, {plen(run):.0f} ft, up to the fixture')
        if wh:
            run = manhattan((mx + 0.3, my), (x + 0.3, y + 0.3), 'y')
            tube('hot', 0.035, [(mx + 0.3, my, 3.0), (mx + 0.3, my, HOT_H)] + flat(run[1:], HOT_H) + [(x + 0.3, y + 0.3, top)], f['id'], f"{f['id']} · hot to {f['name'].lower()}", f'{sup} PEX hot home run under the slab, {plen(run):.0f} ft, up to the fixture')
    for h in HOSE:
        run = manhattan(MANIFOLD, h['at'], 'y')
        tube('cold', 0.05, [(mx, my, 3.0), (mx, my, COLD_H)] + flat(run[1:], COLD_H) + [(*h['at'], 1.5)], h['id'], f"{h['id']} · hose bibb", f"{h['name']}: 3/4\" PEX cold under the slab, {plen(run):.0f} ft")
        out.append(dict(shape='box', m='cold', box=[h['at'][0] - 0.2, h['at'][1] - 0.2, h['at'][0] + 0.2, h['at'][1] + 0.2, 1.35, 1.65], ref=h['id'], name=f"{h['id']} · hose bibb", text=h['name']))
    # floor drains (grates at the floor, on this layer and not with the fixtures) and cleanouts
    for f in PLUMBED:
        if f['kind'] == 'drain': out.append(dict(shape='cyl', m='drain', at=f['at'], r=0.27, h=[0.0, 0.04], ref=f['id'], name=f"{f['id']} · {f['name']}", text='Floor drain grate; trap and 2" drain under the slab (P-1)'))
    for id, at in [('CO1', (33.0, 53.0)), ('CO2', (31.6, 35.5)), ('CO3', (79.6, 46.6))]:
        tube('drain', 0.13 if id != 'CO1' else 0.17, [(*at, DRAIN_H), (*at, 0.05)], id, f'{id} · cleanout', '4" cleanout to the floor' if id == 'CO1' else '3" cleanout to the floor at a change of direction')
    return out


if __name__ == '__main__':
    print(build()['summary'])
