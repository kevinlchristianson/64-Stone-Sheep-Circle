"""E-1 Electrical: a first-draft device layout, circuit schedule and service load calculation.

The plan set has no electrical sheet, so every device here is placed by rule
from the rooms, doors and fixtures in plan/house.json, to NEC 2023 minimums
plus the usual builder extras (it's a starting point for the electrician and
the owner's walk-through, not a design they have signed off):

- general receptacles so no point along a wall is more than 6 ft from one
  (210.52(A)), counter receptacles every 4 ft in the kitchen, one at each
  bath vanity, hall receptacle where a hall is 10 ft or longer
- a light in every room, switched at the door you walk in through
- smoke alarms in every sleeping room, outside each sleeping area and on the
  living level; CO alarms outside the sleeping areas (attached garage, wood
  fireplace)
- dedicated circuits for the kitchen appliances, laundry, mechanical
  equipment and garage door openers
Tags: R receptacles, S switches, L lights, F fans, A dedicated appliances, D alarms.
"""
import math
from setlib import HOUSE, ROOMS, Sheet, ft_in, centroid, bbox, esc, px, py, S as SC

ELEC = '#c8650a'
HEATED = [r for r in HOUSE['rooms'] if r['kind'] not in ('garage', 'outdoor')]
DOORS = HOUSE['doors']
SLEEP = {'master_bed', 'bed1', 'bed2', 'bed3', 'office'}   # the office has a closet-free door off the entry, but counts as a possible bedroom for alarms
PANEL = dict(id='P1', at=(25.6, 40.0), name='Main panel P1, 200 A', room='garage')


def edges(room):
    p = room['poly']
    for i in range(len(p)):
        yield p[i], p[(i + 1) % len(p)]


def wall_segments(room):
    """The room's wall lengths, broken at doors and openings (NEC: wall space stops at a doorway)."""
    out = []
    for (x0, y0), (x1, y1) in edges(room):
        horiz = abs(y1 - y0) < 1e-6
        a0, a1 = sorted((x0, x1) if horiz else (y0, y1)); line = y0 if horiz else x0
        cuts = []
        for d in DOORS:
            if d['kind'] == 'glass': continue
            if d['axis'] == ('y' if horiz else 'x') and abs(d['at'] + (0.15 if not d.get('ext') else 0.23) - line) < 0.5:
                cuts.append(tuple(d['span']))
        if room['id'] == 'living' and horiz and abs(line - 42.48) < 0.1: cuts.append((43.7, 51.1))   # open to the entry
        if room['id'] == 'kitchen' and not horiz and abs(line - 43.707) < 0.1: cuts.append((16.1, 42.5))  # open to living
        if room['id'] in ('kitchen', 'dining') and horiz and abs(line - 16.12) < 0.1: cuts.append((30.8, 43.8))
        if room['id'] == 'living' and not horiz and abs(line - 43.707) < 0.1: cuts.append((16.8, 42.5))
        segs = [(a0, a1)]
        for c0, c1 in cuts:
            nxt = []
            for s0, s1 in segs:
                if c1 <= s0 or c0 >= s1: nxt.append((s0, s1)); continue
                if c0 > s0: nxt.append((s0, c0))
                if c1 < s1: nxt.append((c1, s1))
            segs = nxt
        for s0, s1 in segs:
            if s1 - s0 >= 2.0:
                out.append(dict(horiz=horiz, line=line, a0=s0, a1=s1, inward=inward(room, horiz, line, (s0 + s1) / 2)))
    return out


def inward(room, horiz, line, a):
    cx, cy = centroid(room)
    if horiz: return 1 if cy > line else -1
    return 1 if cx > line else -1


def build():
    sh = Sheet('E-1', 'Electrical', 'First-draft device layout to NEC 2023 minimums, for the electrician to lay out and the owner to walk through.')
    sh.base()
    devices = []   # dict(id, kind, at, room, desc, ckt, h)

    def dev(kind, at, room, desc, h=None, ckt=None):
        devices.append(dict(kind=kind, at=at, room=room, desc=desc, h=h, ckt=ckt))

    # ---- receptacles
    for r in HEATED:
        rid = r['id']
        if r['kind'] in ('closet', 'mech') or rid in ('master_hall', 'entry', 'coat'):
            continue
        if rid == 'kitchen':
            for i in range(4): dev('rec-gfci', (31.4, 23.8 + i * 3.6 + (1.2 if i >= 2 else 0)), rid, 'Counter receptacle, GFCI, 20 A', 44 / 12)
            dev('rec-gfci', (36.6, 29.0), rid, 'Island receptacle, GFCI (side of island)', 1.0)
            dev('rec-gfci', (40.8, 32.5), rid, 'Island receptacle, GFCI (side of island)', 1.0)
            dev('rec-gfci', (33.6, 44.55), rid, 'Counter receptacle, GFCI', 44 / 12)
            continue
        if r['kind'] == 'bath':
            for f in HOUSE['fixtures']:
                if f['room'] == rid and f['kind'] == 'lav':
                    x, y = f['at']
                    if rid == 'master_bath': at = (16.0, y + 1.1)
                    elif rid == 'bath1': at = (82.8, y - 1.2)
                    elif rid == 'bath2': at = (x + 1.1, 39.8)
                    else: at = (25.25, 23.0)
                    dev('rec-gfci', at, rid, 'Vanity receptacle, GFCI, 20 A bath circuit', 40 / 12)
            continue
        if rid == 'laundry':
            dev('rec-20', (24.55, 23.3), rid, 'Washer receptacle, 20 A dedicated', 3.5)
            dev('rec-240', (24.55, 20.6), rid, 'Dryer receptacle, 30 A 240 V (NEMA 14-30)', 3.0)
            dev('rec-gfci', (16.7, 21.0), rid, 'Counter receptacle, GFCI', 44 / 12)
            continue
        if rid == 'hall':
            dev('rec', (64.65, 30.0), rid, 'Hall receptacle (hall over 10 ft)', 1.33)
            continue
        if rid == 'mud':
            dev('rec', (16.6, 33.5), rid, 'Receptacle', 1.33); dev('rec', (30.3, 34.5), rid, 'Receptacle', 1.33)
            continue
        for s in wall_segments(r):
            L = s['a1'] - s['a0']; n = max(1, math.ceil(L / 12))
            for i in range(n):
                a = s['a0'] + (i + 0.5) * L / n
                off = 0.25 * s['inward']
                at = (a, s['line'] + off) if s['horiz'] else (s['line'] + off, a)
                desc = 'Receptacle, tamper-resistant, AFCI/GFCI dual function' if rid in ('dining',) else 'Receptacle, tamper-resistant, AFCI'
                dev('rec', at, rid, desc, 1.33)
    # garage and outside
    for at in [(0.8, 39.0), (0.8, 52.1), (0.8, 65.5), (8.0, 66.8), (22.5, 69.3), (30.2, 60.0), (30.2, 45.0), (10.0, 37.5)]:
        dev('rec-gfci', at, 'garage', 'Garage receptacle, GFCI', 3.5)
    dev('rec-gfci', (8.0, 46.0), 'garage', 'Ceiling receptacle for door opener 1, GFCI', 10.0)
    dev('rec-gfci', (8.0, 58.6), 'garage', 'Ceiling receptacle for door opener 2, GFCI', 10.0)
    for at, rm in [((40.0, 54.3), 'porch'), ((63.0, 54.3), 'porch'), ((47.0, 15.8), 'patio'), ((63.4, 9.0), 'patio')]:
        dev('rec-wr', at, rm, 'Exterior receptacle, GFCI, weather-resistant in-use cover', 1.5)

    # ---- dedicated appliances
    dev('appl', (31.2, 29.6), 'kitchen', '48" range: 50 A 240 V range receptacle if electric (confirm fuel; a dual-fuel range needs gas + 120 V)', 0.5)
    dev('appl', (39.4, 26.2), 'kitchen', 'Dishwasher, 20 A (island)', 1.0)
    dev('appl', (39.4, 27.6), 'kitchen', 'Disposal, 20 A, switched at the island', 1.0)
    dev('appl', (37.9, 44.6), 'kitchen', 'Refrigerator, 20 A dedicated', 4.0)
    dev('appl', (31.2, 31.9), 'kitchen', 'Range hood, 15 A (over the range)', 6.5)
    dev('appl', (33.6, 47.2), 'mechanical', 'Air handler / furnace: dedicated circuit per the equipment picked', 5.0)
    dev('appl', (31.2, 51.5), 'mechanical', 'Water heater: 30 A 240 V if electric or heat-pump (confirm)', 5.0)
    dev('appl', (3.0, 32.8), 'outside', 'Heat pump / AC condenser, disconnect within sight, 240 V (size per equipment)', 3.0)
    dev('appl', (62.4, 32.0), 'living', 'Fireplace insert blower, 15 A receptacle in the surround', 1.0)
    dev('appl', (14.6, 9.6), 'master_bath', 'Pedestal tub: none needed unless an air or heated tub is picked', None)

    # ---- lights
    def light(at, rid, desc, kind='light', h=None): dev(kind, at, rid, desc, h)
    for r in HEATED + [ROOMS['garage'], ROOMS['porch'], ROOMS['patio']]:
        rid = r['id']; cx, cy = centroid(r)
        x0, y0, x1, y1 = bbox(r)
        if rid == 'kitchen':
            for x in (32.9, 41.6):
                for y in (19.5, 25.5, 35.5, 41.5): light((x, y), rid, 'Recessed 6" LED, vaulted ceiling (sloped trim)', 'can')
            for y in (26.5, 30.6, 34.7): light((38.68, y), rid, 'Island pendant', 'pend')
            light((32.0, 24.0), rid, 'Under-cabinet LED strip, left wall', 'strip'); continue
        if rid == 'living':
            for x in (47.5, 54.0, 60.5):
                for y in (21.5, 37.5): light((x, y), rid, 'Recessed 6" LED, vaulted ceiling (sloped trim)', 'can')
            light((54.0, 29.6), rid, 'Ceiling fan with light, fan-rated box (vault: downrod)', 'fan'); continue
        if rid == 'dining': light((cx, cy), rid, 'Chandelier over the table, dimmer', 'pend'); continue
        if rid == 'garage':
            for x in (7.5, 22.5):
                for y in (45.0, 60.0): light((x, y), rid, '4 ft LED shop fixture', 'light')
            continue
        if rid == 'porch':
            for x in (37.0, 47.5, 58.0, 70.0): light((x, 58.0), rid, 'Recessed porch light, wet-rated', 'can')
            continue
        if rid == 'patio':
            light((54.1, 8.2), rid, 'Ceiling fan with light, wet-rated, vaulted patio', 'fan')
            light((47.0, 4.0), rid, 'Recessed wet-rated', 'can'); light((61.0, 4.0), rid, 'Recessed wet-rated', 'can'); continue
        if r['kind'] == 'bed':
            light((cx, cy), rid, 'Ceiling fan with light, fan-rated box', 'fan'); continue
        if rid == 'master_bath':
            light((11.0, 9.0), rid, 'Ceiling light', 'light'); light((7.8, 21.2), rid, 'Recessed wet-rated, shower', 'can'); light((11.0, 15.5), rid, 'Pendant over tub (check clearance)', 'pend'); continue
        if r['kind'] == 'bath':
            light((cx, cy - (1.0 if rid == 'bath1' else 0)), rid, 'Ceiling light', 'light')
            if rid != 'powder': light((80.4, 14.1) if rid == 'bath1' else (81.5, 37.2), rid, 'Recessed wet-rated, shower/tub', 'can')
            continue
        if rid == 'hall':
            for y in (23.0, 30.0, 37.0): light((66.5, y), rid, 'Ceiling light', 'light')
            continue
        light((cx, cy), rid, 'Ceiling light', 'light')
    # exterior wall lights at the doors
    for at, desc in [((44.6, 54.2), 'Front door sconce'), ((50.5, 54.2), 'Front door sconce'), ((50.3, 15.9), 'Patio door sconce'), ((57.7, 15.9), 'Patio door sconce'),
                     ((5.2, 36.2), 'Service door light'), ((-0.5, 39.8), 'Garage door light'), ((-0.5, 52.1), 'Garage door light'), ((-0.5, 64.4), 'Garage door light')]:
        dev('wall-light', at, 'outside', desc + ', dark-sky', 6.5)

    # ---- fans and alarms
    for at, rid in [((7.0, 9.0), 'master_bath'), ((7.8, 19.0), 'master_bath'), ((80.0, 9.8), 'bath1'), ((76.0, 37.0), 'bath2'), ((28.0, 25.5), 'powder'), ((20.5, 20.0), 'laundry')]:
        dev('fan', at, rid, 'Exhaust fan, ducted outside, 80 CFM (humidity control on full baths)')
    for rid in sorted(SLEEP):
        cx, cy = centroid(ROOMS[rid]); dev('smoke', (cx + 2.0, cy - 2.0), rid, 'Smoke alarm, interconnected, hardwired with battery backup')
    for at, rid in [((66.5, 26.5), 'hall'), ((27.8, 19.8), 'master_hall'), ((52.0, 34.5), 'living')]:
        dev('smoke-co', at, rid, 'Combination smoke / CO alarm, interconnected, hardwired')

    # ---- switches: inside each room at its doors, on the latch side
    for d in DOORS:
        if d['kind'] in ('glass', 'overhead', 'bypass'): continue
        for rid in d['between']:
            if rid not in ROOMS or ROOMS[rid]['kind'] == 'outdoor': continue
            if ROOMS[rid]['kind'] == 'closet' and rid != 'pantry' and d['kind'] != 'swing': continue
            room = ROOMS[rid]; cx, cy = centroid(room)
            s0, s1 = d['span']; a = d['at']
            t = 0.46 if d.get('ext') else 0.293
            if d['axis'] == 'y':
                side = -1 if cy < a else 1
                y = (a - 0.3) if side < 0 else (a + t + 0.3)
                x = s1 + 0.45 if abs(s1 - cx) < abs(s0 - cx) or True else s0 - 0.45
                at = (min(x, bbox(room)[2] - 0.3), y)
            else:
                side = -1 if cx < a else 1
                x = (a - 0.3) if side < 0 else (a + t + 0.3)
                at = (x, min(s1 + 0.45, bbox(room)[3] - 0.3))
            if not (bbox(room)[0] - 0.1 <= at[0] <= bbox(room)[2] + 0.1 and bbox(room)[1] - 0.1 <= at[1] <= bbox(room)[3] + 0.1): continue
            if rid == 'garage' and d['id'] not in ('D3', 'D6'): continue
            if d['id'] in ('D7',): continue
            dev('switch', at, rid, f"Switch at {d['name']} ({d['id']}): room lights" + (', 3-way' if rid in ('kitchen', 'living', 'mud', 'hall', 'master_hall', 'garage', 'entry') else ''), 4.0)
    dev('switch', (44.4, 52.6), 'entry', 'Switches at the front door: entry light, porch lights, front sconces', 4.0)
    dev('switch', (50.6, 17.3), 'living', 'Switches at the patio doors: patio fan/light, sconces', 4.0)

    # ---- circuits
    circuits = []

    def ckt(name, amps, poles, kind, devs, va, note=''):
        n = len(circuits) + 1
        circuits.append(dict(n=n, name=name, amps=amps, poles=poles, kind=kind, devs=devs, va=va, note=note))
        for d in devs: d['ckt'] = n

    by = lambda pred: [d for d in devices if pred(d) and d.get('ckt') is None]
    # dedicated first
    for d in devices:
        if d['kind'] != 'appl' or d['room'] == 'master_bath': continue
        desc = d['desc']
        if desc.startswith('48" range'): ckt('Range', 50, 2, '240 V', [d], 12000, 'electric range assumed; drop if gas')
        elif desc.startswith('Dishwasher'): ckt('Dishwasher', 20, 1, 'GFCI', [d], 1200)
        elif desc.startswith('Disposal'): ckt('Disposal', 20, 1, 'GFCI', [d], 900)
        elif desc.startswith('Refrigerator'): ckt('Refrigerator', 20, 1, '', [d], 800)
        elif desc.startswith('Range hood'): ckt('Range hood', 15, 1, '', [d], 400)
        elif desc.startswith('Air handler'): ckt('Air handler / furnace', 30, 2, '240 V', [d], 5000, 'size to the equipment; electric strip heat would need 60 A')
        elif desc.startswith('Water heater'): ckt('Water heater', 30, 2, '240 V', [d], 4500, 'heat-pump or electric; drop if gas')
        elif desc.startswith('Heat pump'): ckt('Heat pump / AC', 30, 2, '240 V', [d], 5000, 'size to the equipment nameplate')
        elif desc.startswith('Fireplace'): ckt('Fireplace blower', 15, 1, 'AFCI', [d], 200)
    ckt('Kitchen counter 1 (small appliance)', 20, 1, 'GFCI/AFCI', [d for d in devices if d['room'] == 'kitchen' and d['kind'] == 'rec-gfci'][:4], 1500)
    ckt('Kitchen counter 2 (small appliance)', 20, 1, 'GFCI/AFCI', by(lambda d: d['room'] == 'kitchen' and d['kind'] == 'rec-gfci'), 1500)
    ckt('Washer', 20, 1, 'GFCI/AFCI', by(lambda d: d['kind'] == 'rec-20'), 1500, 'laundry circuit')
    ckt('Dryer', 30, 2, '240 V', by(lambda d: d['kind'] == 'rec-240'), 5000)
    ckt('Laundry counter', 20, 1, 'GFCI/AFCI', by(lambda d: d['room'] == 'laundry' and d['kind'] == 'rec-gfci'), 180)
    ckt('Bath receptacles (all baths)', 20, 1, 'GFCI', by(lambda d: ROOMS.get(d['room'], {}).get('kind') == 'bath' and d['kind'] == 'rec-gfci'), 180 * 6)
    ckt('Garage receptacles', 20, 1, 'GFCI', by(lambda d: d['room'] == 'garage' and d['kind'] == 'rec-gfci' and d['h'] < 5), 180 * 8)
    ckt('Garage door openers', 20, 1, 'GFCI', by(lambda d: d['room'] == 'garage' and d['kind'] == 'rec-gfci'), 1200)
    ckt('Exterior receptacles', 20, 1, 'GFCI', by(lambda d: d['kind'] == 'rec-wr'), 720)
    # general receptacles, grouped by area, up to 8 per circuit
    zones = [('Master suite receptacles', {'master_bed', 'master_bath', 'master_closet', 'master_hall'}),
             ('Dining and mud receptacles', {'dining', 'mud', 'powder'}),
             ('Living receptacles', {'living', 'entry'}),
             ('Office receptacles', {'office'}),
             ('Bedroom 1 receptacles', {'bed1', 'bath1'}),
             ('Bedroom 2 and hall receptacles', {'bed2', 'hall', 'bath2'}),
             ('Bedroom 3 receptacles', {'bed3'})]
    for name, rooms in zones:
        devs = by(lambda d: d['room'] in rooms and d['kind'] == 'rec')
        for i in range(0, len(devs), 8):
            ckt(name + (f' ({i // 8 + 1})' if len(devs) > 8 else ''), 20, 1, 'AFCI', devs[i:i + 8], 180 * len(devs[i:i + 8]))
    # lighting, fans, alarms, switches by zone
    lzones = [('Lights: master suite, laundry, mud, powder', {'master_bed', 'master_bath', 'master_closet', 'master_hall', 'laundry', 'mud', 'powder'}),
              ('Lights: kitchen, dining, pantry', {'kitchen', 'dining', 'pantry', 'mechanical'}),
              ('Lights: living, entry, office, porch, patio', {'living', 'entry', 'office', 'coat', 'porch', 'patio', 'outside'}),
              ('Lights: bedroom wing', {'bed1', 'bed2', 'bed3', 'bath1', 'bath2', 'hall', 'bed1_closet', 'bed2_closet', 'bed3_closet'}),
              ('Lights: garage', {'garage'})]
    for name, rooms in lzones:
        devs = by(lambda d: d['room'] in rooms and d['kind'] in ('light', 'can', 'pend', 'strip', 'fan', 'wall-light', 'switch'))
        ckt(name, 15, 1, 'AFCI' if 'garage' not in name else '', devs, sum(60 if d['kind'] != 'switch' else 0 for d in devs))
    ckt('Smoke / CO alarms (interconnected)', 15, 1, 'AFCI', by(lambda d: d['kind'] in ('smoke', 'smoke-co')), 50)
    for d in devices:
        if d['ckt'] is None and d['kind'] != 'appl': print('unassigned', d)

    # ---- tags and drawing
    prefix = {'rec': 'R', 'rec-gfci': 'R', 'rec-20': 'R', 'rec-240': 'R', 'rec-wr': 'R', 'switch': 'S', 'light': 'L', 'can': 'L', 'pend': 'L', 'strip': 'L', 'wall-light': 'L', 'fan': 'F', 'appl': 'A', 'smoke': 'D', 'smoke-co': 'D'}
    count = {}
    picks, rows = {}, []
    for d in devices:
        p = prefix[d['kind']]; count[p] = count.get(p, 0) + 1
        d['id'] = f'{p}{count[p]}'
    for d in devices:
        x, y = d['at']
        c = circuits[d['ckt'] - 1] if d.get('ckt') else None
        rm = ROOMS[d['room']]['name'] if d['room'] in ROOMS else 'Outside'
        title = f"{d['id']} · {d['desc']}" + (f" · circuit {c['n']}" if c else '')
        sh.open_group(d['id'], title, hit=(x, y, 0.7), attrs=f' data-ckt="{c["n"]}"' if c else '')
        symbol(sh, d, x, y)
        sh.close_group()
        fields = [('Device', d['desc']), ('Room', rm), ('Position', f"{ft_in(x)} from the garage-door wall, {ft_in(y)} from the rear wall")]
        if d['h'] is not None: fields.append(('Height', f"{ft_in(d['h'])} to center" if d['h'] < 9 else 'ceiling'))
        if c: fields.append(('Circuit', f"{c['n']}: {c['name']} ({c['amps']} A{', ' + c['kind'] if c['kind'] else ''})"))
        picks[d['id']] = dict(tag=d['id'], sub=rm, fields=fields, ckt=c['n'] if c else None)
        rows.append((d['id'], [d['id'], d['desc'], rm, (f"{ft_in(d['h'])}" if d['h'] is not None and d['h'] < 9 else 'ceiling' if d['h'] else '—'), str(c['n']) if c else '—']))
    # panel
    x, y = PANEL['at']
    sh.open_group('P1', PANEL['name'], hit=(x, y, 0.9))
    sh.rect(x - 0.35, y - 1.2, x + 0.35, y + 1.2, '#fff', ELEC, 1.4)
    sh.text(x + 1.0, y, 'P1', 7, ELEC, '700', rot=90)
    sh.close_group()

    # ---- load calculation, NEC 220.82 (optional method, dwelling)
    sq = HOUSE['totals']['heated_gross_sf']
    general = 3 * sq + 2 * 1500 + 1500
    appl = sum(c['va'] for c in circuits if c['name'] in ('Range', 'Dishwasher', 'Disposal', 'Refrigerator', 'Range hood', 'Water heater', 'Dryer', 'Fireplace blower', 'Garage door openers'))
    other = general + appl
    demand_other = 10000 + 0.4 * (other - 10000)
    hvac = 10000   # heat pump + 5 kW backup heat, 100% (220.82(C)); replaced once equipment is picked
    total = demand_other + hvac
    amps = total / 240
    load = dict(sq=sq, general=general, appl=appl, demand=round(demand_other), hvac=hvac, total=round(total), amps=round(amps))
    load_rows = [
        (None, ['General lighting & receptacles', f'3 VA × {sq:,} sf', f'{3 * sq:,} VA']),
        (None, ['Small-appliance circuits', '2 × 1,500 VA', '3,000 VA']),
        (None, ['Laundry circuit', '1 × 1,500 VA', '1,500 VA']),
        (None, ['Fixed appliances', 'range, DW, disposal, fridge, hood, water heater, dryer, blower, openers', f'{appl:,} VA']),
        (None, ['All other load, demand', 'first 10 kVA at 100 %, rest at 40 % (220.82(B))', f'{demand_other:,.0f} VA']),
        (None, ['Heating / cooling', 'heat pump with 5 kW backup, at 100 % (assumed)', f'{hvac:,} VA']),
        (None, ['Calculated load', f'{total:,.0f} VA ÷ 240 V', f'{amps:,.0f} A → 200 A service']),
    ]
    ckt_rows = []
    sp = 1
    for c in circuits:
        slots = f'{sp}' if c['poles'] == 1 else f'{sp}, {sp + 2}'
        sp += 2 * c['poles'] if False else c['poles']
        ckt_rows.append((f'ckt-{c["n"]}', [str(c['n']), c['name'], f"{c['amps']} A", f"{c['poles']}-pole", c['kind'] or '—', '12 AWG' if c['amps'] == 20 else '14 AWG' if c['amps'] == 15 else '10 AWG' if c['amps'] == 30 else '6 AWG' if c['amps'] == 50 else '—',
                                            str(len(c['devs'])), c['note'] or '—']))
    spaces = sum(c['poles'] for c in circuits)
    notes = [
        f'Main panel P1, 200 A, in the garage on the wall to the mud room (W43), {spaces} spaces used of a 40-space panel. Penetrations through the garage wall fire-caulked.',
        'Service size from the NEC 220.82 calculation below: about ' + f"{amps:,.0f} A with a heat pump assumed; 200 A leaves room for an EV charger (add a 50 A 240 V circuit in the garage if wanted).",
        'AFCI on every 120 V 15/20 A branch circuit in the living spaces (210.12); GFCI in baths, kitchen counters, laundry, garage, outdoors, dishwasher (210.8).',
        'Tamper-resistant receptacles throughout (406.12). Receptacles at 16" to center, counters 44", vanity 40".',
        'Smoke alarms in every bedroom, outside the sleeping areas and on the living level; combination smoke/CO in the halls outside the sleeping areas (attached garage and wood fireplace); all interconnected.',
        'Kitchen and living ceilings are vaulted 4:12: sloped-ceiling recessed housings and a fan downrod sized for the slope.',
        'Device positions are drawn to the room, not measured to studs: the electrician sets final boxes at the walk-through.',
    ]
    open_items = [
        'Range fuel: the 48" range (BS655Z-48) could be gas, dual-fuel or electric. Electric is assumed (50 A 240 V); a gas or dual-fuel range drops that circuit and adds a gas line.',
        'Heating and water heating fuel (heat pump / gas furnace / electric) set the mechanical circuits and the service load.',
        'Meter and service entrance location (overhead or underground, which side of the house) is not on the site plan.',
        'EV charger in the garage: yes or no.',
        'Lighting choices (cans vs. surface fixtures, pendants, fan locations) for the owner\'s walk-through.',
        'Low-voltage: network drops, TV at the fireplace wall, doorbell, security.',
    ]
    sh.title_block(['Receptacles R, switches S, lights L, fans F, appliances A, alarms D.', 'Pick a device for its circuit; pick a circuit row to light up everything on it.', f'Main panel P1 in the garage. Calculated load {amps:,.0f} A; 200 A service.'])
    tables = [
        dict(key='circuits', title='Circuit schedule, main panel P1', cols=['Ckt', 'Serves', 'Breaker', 'Poles', 'Protection', 'Wire (Cu)', 'Devices', 'Notes'], rows=ckt_rows, ckt=True),
        dict(key='devices', title='Device schedule', cols=['Tag', 'Device', 'Room', 'Height', 'Ckt'], rows=rows),
        dict(key='load', title='Service load calculation (NEC 220.82)', cols=['Item', 'Basis', 'Load'], rows=load_rows),
    ]
    summary = dict(devices=len(devices), circuits=len(circuits), spaces=spaces, amps=round(amps),
                   receptacles=sum(1 for d in devices if d['kind'].startswith('rec')), lights=sum(1 for d in devices if d['kind'] in ('light', 'can', 'pend', 'strip', 'wall-light')),
                   switches=sum(1 for d in devices if d['kind'] == 'switch'))
    bom = [(None, ['Duplex receptacles, TR', str(sum(1 for d in devices if d['kind'] == 'rec')), '15 A, plus boxes']),
           (None, ['GFCI receptacles', str(sum(1 for d in devices if d['kind'] in ('rec-gfci', 'rec-wr'))), '20 A, weather-resistant outside with in-use covers']),
           (None, ['Dedicated receptacles', str(sum(1 for d in devices if d['kind'] in ('rec-20', 'rec-240'))), 'washer 20 A, dryer 14-30R']),
           (None, ['Switches', str(summary['switches']), 'single-pole and 3-way, dimmers in living, dining, master']),
           (None, ['Light fixtures', str(summary['lights']), 'including recessed and exterior']),
           (None, ['Ceiling fans', str(sum(1 for d in devices if d['kind'] == 'fan' and 'Ceiling fan' in d['desc'])), 'fan-rated boxes']),
           (None, ['Exhaust fans', str(sum(1 for d in devices if d['kind'] == 'fan' and 'Exhaust' in d['desc'])), '80 CFM, ducted to outside']),
           (None, ['Smoke and smoke/CO alarms', str(sum(1 for d in devices if d['kind'].startswith('smoke'))), 'hardwired, interconnected']),
           (None, ['Panel', '1', '200 A main breaker, 40 spaces, AFCI/GFCI breakers per schedule']),
           (None, ['NM-B 14/2 and 12/2', f"~{round(len(devices) * 22 / 250) * 250:,} ft", 'rough order from device count (about 22 ft per device)'])]
    tables.append(dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the device layout, for pricing. The electrician takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=bom))
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, load=load, circuits=[dict(n=c['n'], name=c['name']) for c in circuits],
                devices=[dict(id=d['id'], at=d['at'], h=d['h'], desc=d['desc'], kind=d['kind']) for d in devices])


def symbol(sh, d, x, y):
    k = d['kind']; c = ELEC
    if k.startswith('rec'):
        sh.circle(x, y, 0.32, '#fff', c, 1.1)
        sh.line(x - 0.12, y - 0.15, x - 0.12, y + 0.15, c, 0.9); sh.line(x + 0.12, y - 0.15, x + 0.12, y + 0.15, c, 0.9)
        if k != 'rec': sh.text(x + 0.62, y - 0.45, {'rec-gfci': 'G', 'rec-20': '20', 'rec-240': '240', 'rec-wr': 'WR'}[k], 5, c, '700')
    elif k == 'switch':
        sh.text(x, y, 'S', 7, c, '700')
    elif k == 'light':
        sh.circle(x, y, 0.42, '#fff', c, 1.1); sh.line(x - 0.3, y - 0.3, x + 0.3, y + 0.3, c, 0.8); sh.line(x - 0.3, y + 0.3, x + 0.3, y - 0.3, c, 0.8)
    elif k == 'can':
        sh.circle(x, y, 0.3, '#fff', c, 1.0); sh.circle(x, y, 0.12, c, c, 0)
    elif k == 'pend':
        sh.circle(x, y, 0.4, '#fff', c, 1.0); sh.text(x, y, 'P', 5, c, '700')
    elif k == 'strip':
        sh.rect(x - 0.15, y - 2.5, x + 0.15, y + 2.5, '#fff', c, 0.8)
    elif k == 'wall-light':
        sh.circle(x, y, 0.32, c, c, 0)
    elif k == 'fan':
        sh.rect(x - 0.45, y - 0.45, x + 0.45, y + 0.45, '#fff', c, 1.0); sh.text(x, y, 'F', 6, c, '700')
    elif k == 'appl':
        sh.rect(x - 0.38, y - 0.38, x + 0.38, y + 0.38, '#fff', c, 1.1); sh.text(x, y, 'A', 6, c, '700')
    elif k in ('smoke', 'smoke-co'):
        sh.circle(x, y, 0.45, '#fff', '#b4462f', 1.0); sh.text(x, y, 'SD' if k == 'smoke' else 'CO', 4.6, '#b4462f', '700')


if __name__ == '__main__':
    b = build()
    print(b['summary'], b['load'])
