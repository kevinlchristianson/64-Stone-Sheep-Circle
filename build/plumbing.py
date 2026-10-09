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
            arm = manhattan(f['at'], s['at'], 'y' if f['room'] in ('bath1', 'bath2') else 'x')
            sh.path(arm, DRAIN, 1.3)
            drain_lf['2"' if f['kind'] in ('shower', 'washer', 'drain') else '3"' if f['kind'] == 'wc' else '1-1/2"'] += plen(arm)
        # supply home runs from the manifold
        if wc: sh.path(manhattan(MANIFOLD, f['at'], 'y'), COLD, 0.7, '1,0', extra=' opacity="0.55"')
        if wh: sh.path(manhattan((MANIFOLD[0] + 0.3, MANIFOLD[1]), (f['at'][0] + 0.3, f['at'][1] + 0.3), 'y'), HOT, 0.7, extra=' opacity="0.55"')
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
    sh.title_block(['Drains black (4" main heavy), floor-drain lines dashed, stacks green.', 'PEX supply home runs: cold blue, hot red.', 'Routing is schematic: the plumber lays out the final runs.'])
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
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, lines=lines, stacks=STACKS, hose=HOSE)


if __name__ == '__main__':
    print(build()['summary'])
