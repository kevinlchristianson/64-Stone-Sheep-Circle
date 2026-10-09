"""M-1 HVAC: room-by-room heating and cooling loads, equipment size, registers and duct layout.

Loads are a simplified Manual J: each room's exterior walls, windows, doors,
ceiling and slab edge from plan/house.json, times a U-value, times the
design temperature difference, plus air leakage shared by exterior wall
area, and for cooling solar gain through the glass, people and appliances.
Envelope values are IECC 2021 climate zone 6 minimums for a new house
(build/climate.py), so the numbers move when the location or the insulation
is settled. Equipment: one ducted heat pump with backup heat, the air handler
in the 3' x 8' mechanical closet, ducts in the attic.
"""
import math
from setlib import HOUSE, ROOMS, Sheet, ft_in, centroid, bbox, room_at
from climate import CLIMATE, ENVELOPE

AIR = '#2c6aa0'; RET = '#4c8c4a'
H = HOUSE['meta']['ceiling_ft']
VAULT = {'kitchen', 'living'}
HEATED = [r for r in HOUSE['rooms'] if r['kind'] not in ('garage', 'outdoor')]
AH = (32.4, 48.9)


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


def build():
    sh = Sheet('M-1', 'HVAC', f"Room loads at {CLIMATE['name']} design conditions, one ducted heat pump with backup heat, ducts in the attic.")
    sh.base()
    loads = [room_load(r) for r in HEATED]
    Qh = sum(l['heat'] for l in loads); Qc = sum(l['cool'] for l in loads)
    Qc_latent = Qc * 0.08
    # cold climate: size the variable-speed heat pump to carry ~90 % of the design heat (it turns down for cooling)
    tons = max(1.5, math.ceil(max((Qc + Qc_latent) / 12000, 0.9 * Qh / (12000 * CLIMATE['hp_capacity_at_design'])) * 2) / 2)
    cfm_sys = tons * 400
    # room airflow: share of the larger of heating and cooling needs
    for l in loads:
        l['cfm'] = max(l['heat'] / Qh, l['cool'] / Qc) * cfm_sys
    k = cfm_sys / sum(l['cfm'] for l in loads)
    for l in loads:
        l['cfm'] *= k
        kind = ROOMS[l['id']]['kind']
        l['regs'] = 0 if kind in ('closet', 'mech') or l['id'] in ('master_hall', 'hall') or (l['cfm'] < 20 and kind != 'bath') else max(1, math.ceil(l['cfm'] / 120))
    picks, rows = {}, []
    # trunks
    east = [AH, (32.4, 48.3), (66.5, 48.3), (66.5, 20.2)]
    west = [AH, (32.4, 48.3), (28.0, 48.3), (28.0, 19.6), (11.0, 19.6)]
    sh.path(east, AIR, 5.5, extra=' opacity="0.35"'); sh.path(west, AIR, 5.5, extra=' opacity="0.35"')
    trunk_pts = []
    for line in (east, west):
        for i in range(len(line) - 1):
            (x0, y0), (x1, y1) = line[i], line[i + 1]
            n = int(max(abs(x1 - x0), abs(y1 - y0)) / 0.5) + 1
            trunk_pts += [(x0 + (x1 - x0) * j / n, y0 + (y1 - y0) * j / n) for j in range(n + 1)]
    reg_n = 0; branch_lf = 0.0; regs = []
    for l in loads:
        r = ROOMS[l['id']]
        spots = register_spots(r, l)
        per = l['cfm'] / max(1, len(spots)) if spots else 0
        size = '6"' if per <= 80 else '7"' if per <= 110 else '8"'
        grille = '4x10' if per <= 80 else '4x12' if per <= 120 else '6x12'
        for (x, y) in spots:
            reg_n += 1; rid = f'SR{reg_n}'
            t = min(trunk_pts, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
            br = [t, (t[0], y), (x, y)] if abs(t[0] - x) > abs(t[1] - y) else [t, (x, t[1]), (x, y)]
            sh.path(br, AIR, 1.1)
            branch_lf += abs(t[0] - x) + abs(t[1] - y)
            title = f"{rid} · supply {grille} on a {size} duct · {per:.0f} CFM · {r['name']}"
            regs.append(dict(id=rid, at=(x, y), name=title))
            sh.open_group(rid, title, hit=(x, y, 0.8))
            sh.rect(x - 0.55, y - 0.3, x + 0.55, y + 0.3, '#fff', AIR, 1.2)
            sh.line(x - 0.4, y, x + 0.4, y, AIR, 0.8)
            sh.close_group()
            picks[rid] = dict(tag=rid, sub=r['name'], fields=[('Grille', f'{grille} ceiling supply' + (', in the vault: high sidewall from the flat-ceiling side' if l['id'] in VAULT else '')),
                                                            ('Duct', f'{size} insulated flex (R-8) from the trunk'), ('Airflow', f'{per:.0f} CFM'),
                                                            ('Room load', f"heat {l['heat']:,.0f} · cool {l['cool']:,.0f} Btu/h")])
        rows.append((None, [r['name'], f"{l['area']:,.0f}", f"{l['ext_wall']:,}", f"{l['glass']:,}", f"{l['heat']:,.0f}", f"{l['cool']:,.0f}", f"{l['cfm']:,.0f}", str(len(spots)), size if spots else '—']))
    # returns
    rets = [('RA1', (66.5, 27.0), 'Hall return, 20x25 filter grille, ceiling', 'hall', 'central return for the bedroom wing; bedrooms get transfer grilles or jump ducts'),
            ('RA2', (62.0, 39.5), 'Living return, 20x30 high sidewall', 'living', 'main return for the great room'),
            ('RA3', (28.0, 19.8), 'Master hall return, 14x20 ceiling', 'master_hall', 'master suite return; jump duct from the master bed'),
            ('RA4', (32.4, 45.6), 'Return plenum into the air handler', 'kitchen', 'sealed return plenum; nothing may draw air from the garage')]
    for rid, (x, y), name, room, note in rets:
        sh.open_group(rid, name, hit=(x, y, 0.9))
        sh.rect(x - 0.7, y - 0.45, x + 0.7, y + 0.45, '#fff', RET, 1.4)
        sh.line(x - 0.5, y - 0.2, x + 0.5, y + 0.2, RET, 0.8); sh.line(x - 0.5, y + 0.2, x + 0.5, y - 0.2, RET, 0.8)
        sh.close_group()
        if rid != 'RA4': sh.path([(x, y), (x, 47.6), (33.4, 47.6)] if rid != 'RA3' else [(x, y), (29.0, 19.8), (29.0, 46.5), (33.0, 46.5)], RET, 2.2, '5,3')
        picks[rid] = dict(tag=rid, sub=ROOMS[room]['name'], fields=[('Grille', name), ('Note', note)])
    for rid in ('master_bed', 'bed1', 'bed2', 'bed3', 'office'):
        r = ROOMS[rid]; d = next(d for d in HOUSE['doors'] if rid in d['between'] and d['kind'] in ('swing', 'french'))
        s0, s1 = d['span']; a = d['at']
        x, y = ((s0 + s1) / 2, a + (1.0 if centroid(r)[1] > a else -0.7)) if d['axis'] == 'y' else (a + (1.0 if centroid(r)[0] > a else -0.7), (s0 + s1) / 2)
        tid = 'TG-' + rid
        sh.open_group(tid, f"Transfer grille / jump duct, {r['name']}", hit=(x, y, 0.7))
        sh.rect(x - 0.4, y - 0.4, x + 0.4, y + 0.4, '#fff', RET, 1.0, '2,1')
        sh.close_group()
        picks[tid] = dict(tag='TG', sub=r['name'], fields=[('Item', 'Jump duct (ceiling to ceiling) or transfer grille, sized ~1 sq in per CFM of the room supply, so the door can close without starving the room')])
    # air handler and outdoor unit
    x, y = AH
    sh.open_group('AH1', 'Air handler AH-1 (heat pump indoor unit with backup heat)', hit=(x, y, 1.0))
    sh.rect(x - 1.0, y - 1.0, x + 1.0, y + 1.0, '#fff', AIR, 1.8); sh.text(x, y, 'AH-1', 5.5, AIR, '700')
    sh.close_group()
    sh.open_group('HP1', 'Heat pump outdoor unit HP-1', hit=(2.5, 32.5, 1.2))
    sh.rect(1.0, 31.0, 4.0, 34.0, '#fff', AIR, 1.8); sh.text(2.5, 32.5, 'HP-1', 5.5, AIR, '700')
    sh.close_group()
    sh.path([(4.0, 32.5), (5.6, 32.5), (5.6, 36.0), (29.6, 36.0), (29.6, 48.9), (31.4, 48.9)], '#8a5a1a', 1.0, '1,2')
    backup = math.ceil(max(0, Qh - tons * 12000 * CLIMATE['hp_capacity_at_design']) / 3412 / 5) * 5
    picks['AH1'] = dict(tag='AH-1', sub='Mechanical closet', fields=[('Equipment', f'{tons:g}-ton variable-speed air handler, {cfm_sys:,.0f} CFM, with {backup} kW backup heat strips'),
                                                                ('Location', 'Mechanical closet off the garage: the closet must be air-sealed from the garage (gasketed door, sealed plenums) because nothing may pull garage air into the house'),
                                                                ('Filter', 'MERV 11 at the air handler'), ('Condensate', 'to the closet floor drain with a secondary pan')])
    picks['HP1'] = dict(tag='HP-1', sub='Outside, by the master closet wall', fields=[('Equipment', f'{tons:g}-ton cold-climate heat pump (keeps ~{CLIMATE["hp_capacity_at_design"] * 100:.0f} % of rated capacity at {CLIMATE["heat_design_f"]:.0f}°F)'),
                                                                                   ('Line set', 'to AH-1 through the garage attic; ~40 ft'), ('Pad', 'on a raised stand above the snow line, with a disconnect in sight')])
    # ventilation: a balanced ERV is the IECC zone 6 default for a tight house
    sh.open_group('ERV1', 'ERV-1, balanced ventilation', hit=(30.0, 46.0, 0.9))
    sh.rect(29.4, 45.4, 30.6, 46.6, '#fff', '#7a5ca8', 1.4); sh.text(30.0, 46.0, 'ERV', 4.8, '#7a5ca8', '700')
    sh.close_group()
    vent = 0.03 * HOUSE['totals']['heated_gross_sf'] + 7.5 * 5
    picks['ERV1'] = dict(tag='ERV-1', sub='Garage wall, by the mechanical closet', fields=[('Equipment', f'Energy recovery ventilator, {vent:.0f} CFM continuous (ASHRAE 62.2: 0.03 cfm/sf + 7.5 cfm per person, 4 bedrooms + 1)'),
                                                                                     ('Ducts', 'fresh air into the AH-1 return; exhaust from the baths\' general areas, or standalone with its own runs')])
    reg_total = reg_n
    total_rows = [
        (None, ['Heating load', f'{Qh:,.0f} Btu/h', f"{CLIMATE['indoor_heat_f']}°F inside, {CLIMATE['heat_design_f']}°F outside"]),
        (None, ['Cooling load', f'{Qc:,.0f} sensible + {Qc_latent:,.0f} latent Btu/h', f"{CLIMATE['indoor_cool_f']}°F inside, {CLIMATE['cool_design_f']}°F outside"]),
        (None, ['Heat pump', f'{tons:g} tons, {cfm_sys:,.0f} CFM', 'sized to cooling (Manual S); cold-climate model']),
        (None, ['Backup heat', f'{backup} kW', 'covers what the heat pump can\'t at the heating design temperature']),
        (None, ['Supply registers', str(reg_total), '4x10 to 6x12 ceiling, 6-8" R-8 flex']),
        (None, ['Ventilation', f'{vent:.0f} CFM ERV', 'ASHRAE 62.2 continuous']),
    ]
    notes = [
        f"Design conditions: {CLIMATE['name']} ({CLIMATE['source']}). Heating {CLIMATE['heat_design_f']}°F, cooling {CLIMATE['cool_design_f']}°F; inside {CLIMATE['indoor_heat_f']}°F / {CLIMATE['indoor_cool_f']}°F. Location to confirm: these change with it.",
        f"Envelope: walls U-{ENVELOPE['wall_u']} (R-20 + R-5 ci), ceiling R-49 (vault R-38), windows U-{ENVELOPE['window_u']} SHGC {ENVELOPE['window_shgc']}, slab edge R-10, {ENVELOPE['ach50']} ACH50 (IECC 2021 zone 6).",
        'One ducted cold-climate heat pump; the air handler fits the 3\'x8\' mechanical closet (about 22"x22" footprint, return plenum below or beside). Trunks run in the attic over the flat ceilings: east along the front band and up the bedroom hall, west over the mud room and master hall.',
        'The kitchen and living vault (4:12) has no flat attic over it: its supplies are high-sidewall grilles fed from the flat-ceiling attics beside it, or soffit runs.',
        'Ducts in the attic: sealed and tested (≤ 4 CFM25 per 100 sf), R-8 insulation, buried under the attic insulation where possible.',
        'Every bedroom gets a return path (transfer grille or jump duct). Bath fans and the range hood exhaust outside (E-1); a range hood over 400 CFM needs makeup air.',
        'The wood fireplace insert needs its own outside combustion-air kit and a listed chimney.',
    ]
    open_items = [
        'Location: the design temperatures, and with them every number on this sheet, use Casper, WY until the site is confirmed.',
        'Fuel: heat pump with electric backup is assumed. A gas furnace with AC is the other common choice; it needs a gas line, a flue and combustion air in the closet.',
        'Mechanical closet opens from the garage: confirm the AHJ allows the air handler there, and air-seal it (gasketed door, sealed plenum, no return openings).',
        'Insulation values and air-tightness target for the house.',
        'Outdoor unit location (drawn by the master closet\'s outside wall, out of sight from the front).',
    ]
    sh.title_block(['Supplies blue on the trunks; returns green dashed.', 'AH-1 in the mechanical closet, HP-1 outside, ERV-1 for fresh air.', f'{tons:g} tons · heat {Qh / 1000:,.0f} kBtu/h · cool {Qc / 1000:,.0f} kBtu/h'])
    tables = [
        dict(key='rooms', title='Room loads and airflow', cols=['Room', 'Floor sf', 'Ext. wall sf', 'Glass sf', 'Heat Btu/h', 'Cool Btu/h', 'CFM', 'Registers', 'Duct'], rows=rows),
        dict(key='system', title='System', cols=['Item', 'Size', 'Basis'], rows=total_rows),
        dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the layout, for pricing. The HVAC contractor takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=[
            (None, ['Heat pump + air handler', '1 set', f'{tons:g} tons, cold-climate, variable speed, {backup} kW strips']),
            (None, ['Supply registers', str(reg_total), 'ceiling and high sidewall, with boots']),
            (None, ['Return grilles', '3', 'filter grille in the hall, living and master hall']),
            (None, ['Transfer grilles / jump ducts', '5', 'bedrooms and office']),
            (None, ['Trunk duct', f"{sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for line in (east, west) for a, b in zip(line, line[1:])):.0f} ft", 'rigid sheet metal, sealed, R-8 wrap']),
            (None, ['Flex duct, 6-8"', f'{branch_lf * 1.25:.0f} ft', 'R-8, + 25 %']),
            (None, ['Return duct', '~60 ft', '14-16" R-8']),
            (None, ['ERV', '1', f'{vent:.0f} CFM']),
            (None, ['Line set + pad + disconnect', '1', '~40 ft']),
        ]),
    ]
    summary = dict(heat=round(Qh), cool=round(Qc), tons=tons, cfm=cfm_sys, registers=reg_total, backup_kw=backup)
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, loads=loads, regs=regs, trunks=[east, west])


def register_spots(r, l):
    if l['regs'] == 0: return []
    x0, y0, x1, y1 = bbox(r)
    ex = [e for e in l['exposures'] if e['kind'] == 'outside']
    n = l['regs']
    if r['id'] in ('kitchen',): return [(31.6, 20.0 + i * 8.0) for i in range(n)]
    if r['id'] == 'living': return [(46.0 + i * (16.0 / max(1, n - 1)), 18.0) if i % 2 == 0 else (46.0 + i * (16.0 / max(1, n - 1)), 41.0) for i in range(n)]
    if not ex:
        cx, cy = centroid(r); return [(cx, cy)]
    e = max(ex, key=lambda e: e['len'])
    spots = []
    for i in range(n):
        a = e['a0'] + (i + 0.5) * (e['a1'] - e['a0']) / n
        inset = 1.6
        if e['horiz']: spots.append((a, e['line'] + (inset if e['line'] < (y0 + y1) / 2 else -inset)))
        else: spots.append((e['line'] + (inset if e['line'] < (x0 + x1) / 2 else -inset), a))
    return spots


if __name__ == '__main__':
    b = build()
    print(b['summary'])
    for l in b['loads']: print(f"{l['name']:20s} {l['heat']:8.0f} {l['cool']:8.0f} {l['cfm']:5.0f} {l['regs']}")
