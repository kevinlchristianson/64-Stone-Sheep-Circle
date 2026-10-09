"""S-1 Framing: wall runs, door and window rough openings, headers, lumber and drywall take-offs.

Walls come from plan/house.json (the A-1 drawing's own wall rectangles), merged
into runs across the door and window gaps. Exterior walls are 2x6 as drawn;
interior 2x4, except wet walls (a toilet, tub, shower, sink or washer backs
onto them), which go 2x6. Roof framing isn't on the plans: trusses bearing on
the exterior walls are assumed, so interior walls are non-bearing.
"""
import math
from setlib import HOUSE, ROOMS, Sheet, ft_in, centroid, room_at

CEILING = HOUSE['meta']['ceiling_ft']
WET = {'wc', 'lav', 'tub', 'shower', 'washer', 'sink', 'dw'}
OPENINGS = [dict(o, otype='window') for o in HOUSE['windows']] + [dict(d, otype='door') for d in HOUSE['doors'] if d['kind'] != 'glass']


def runs():
    """Merge the drawing's wall rectangles into runs along one line, across opening gaps."""
    segs = []
    for w in HOUSE['walls']:
        horiz = (w['x1'] - w['x0']) >= (w['y1'] - w['y0'])
        segs.append(dict(w, horiz=horiz))
    groups = {}
    for s in segs:
        key = (s['kind'], s['horiz'], round(s['y0'], 2), round(s['y1'], 2)) if s['horiz'] else (s['kind'], s['horiz'], round(s['x0'], 2), round(s['x1'], 2))
        groups.setdefault(key, []).append(s)
    out = []
    for key, ss in groups.items():
        kind, horiz = key[0], key[1]
        ss.sort(key=lambda s: s['x0'] if horiz else s['y0'])
        cur = None
        for s in ss:
            a0, a1 = (s['x0'], s['x1']) if horiz else (s['y0'], s['y1'])
            if cur is not None:
                gap = (cur['a1'], a0)
                line = (key[2] + key[3]) / 2
                bridged = gap[1] - gap[0] < 0.1 or any(
                    o['axis'] == ('y' if horiz else 'x') and abs(o['at'] - line) < 0.6 and abs(o['span'][0] - gap[0]) < 0.4 and abs(o['span'][1] - gap[1]) < 0.4
                    for o in OPENINGS)
                if bridged:
                    cur['a1'] = max(cur['a1'], a1); continue
                out.append(cur)
            cur = dict(kind=kind, horiz=horiz, c0=key[2], c1=key[3], a0=a0, a1=a1)
        out.append(cur)
    for r in out:
        r['len'] = r['a1'] - r['a0']
        r['t'] = r['c1'] - r['c0']
        r['line'] = (r['c0'] + r['c1']) / 2
    # drop stubs fully inside another run's thickness band (corner fillers)
    out = [r for r in out if r['len'] > 0.4]
    # exterior first, then interior; each by position, rear to front, left to right
    out.sort(key=lambda r: (r['kind'] != 'E', round(r['line'] if r['horiz'] else r['a0'], 1), r['a0'] if r['horiz'] else r['line']))
    for i, r in enumerate(out, 1):
        r['id'] = f'W{i}'
        r['openings'] = [o for o in OPENINGS if o['axis'] == ('y' if r['horiz'] else 'x') and abs(o['at'] - r['line']) < 0.6
                         and o['span'][0] >= r['a0'] - 0.3 and o['span'][1] <= r['a1'] + 0.3]
        r['rooms'] = sides(r)
        wet = [f for f in HOUSE['fixtures'] if f['kind'] in WET and near(r, f)]
        r['wet'] = bool(wet) and r['kind'] == 'I'
        r['type'] = '2x6 exterior' if r['kind'] == 'E' else ('2x6 wet wall' if r['wet'] else '2x4 partition')
        r['garage'] = 'garage' in r['rooms'] and any(n not in ('garage', 'outside', 'porch') for n in r['rooms'])
    return out


def near(r, f):
    x, y = f['at']; w, h = f['size']
    if r['horiz']:
        return r['a0'] - 0.2 <= x <= r['a1'] + 0.2 and min(abs(y - h / 2 - r['c1']), abs(y + h / 2 - r['c0'])) < 0.9
    return r['a0'] - 0.2 <= y <= r['a1'] + 0.2 and min(abs(x - w / 2 - r['c1']), abs(x + w / 2 - r['c0'])) < 0.9


def sides(r):
    names = []
    for frac in (0.25, 0.5, 0.75):
        a = r['a0'] + r['len'] * frac
        for off in (-0.4, r['t'] + 0.4):
            x, y = (a, r['c0'] + off) if r['horiz'] else (r['c0'] + off, a)
            rm = room_at(x, y)
            if not rm and r['kind'] != 'E': continue
            n = rm['id'] if rm else 'outside'
            if n not in names: names.append(n)
    return names


def header(o, ext):
    """Header by rough-opening width. Exterior walls carry the roof (trusses), interior ones nothing."""
    ro = o['w'] + (2 / 12 if o['otype'] == 'door' else 0.5 / 12)
    if o.get('kind') == 'opening' and not ext:
        return 'flat 2x4 + cripples (non-bearing)'
    if not ext:
        return '2-2x4 on flat (non-bearing)' if ro <= 4 else '2-2x6 (non-bearing)'
    if ro <= 3.5: return '2-2x8 + 1/2" ply, 1 jack each end'
    if ro <= 5.0: return '2-2x10 + 1/2" ply, 1 jack each end'
    if ro <= 6.5: return '2-2x12 + 1/2" ply, 2 jacks each end'
    return '3-1/2" x 11-7/8" LVL (engineer to confirm), 2 jacks each end'


def rough(o):
    if o['otype'] == 'door':
        if o['kind'] == 'overhead': return f"{ft_in(o['w'] + 0.0)} x {ft_in(o['h'] + 0.0)} (door maker's RO)"
        if o['kind'] == 'opening': return f"{ft_in(o['w'])} x {ft_in(o['h'])} cased"
        if o['kind'] == 'pocket': return f"{ft_in(2 * o['w'] + 1 / 12)} x {ft_in(o['h'] + 2.5 / 12)} (pocket frame)"
        return f"{ft_in(o['w'] + 2 / 12)} x {ft_in(o['h'] + 2.5 / 12)}"
    return f"{ft_in(o['w'] + 0.5 / 12)} x {ft_in(o['h'] + 0.5 / 12)}"


def studs(r):
    """Stud count for a run: 16" o.c. layout, +2 at each end for corners and T's, kings and jacks at each opening."""
    n = math.ceil(r['len'] * 12 / 16) + 1 + 4
    for o in r['openings']:
        jacks = 4 if o['w'] > 6 else 2
        n += 2 + jacks - max(0, math.floor(o['w'] * 12 / 16) - 1)   # kings + jacks, less the studs the opening removes
    return max(n, 3)


def build():
    R = runs()
    sh = Sheet('S-1', 'Framing', 'Wall types, door and window rough openings, headers and blocking. Walls numbered W1 up, exterior first.')
    sh.base()
    col = {'2x6 exterior': '#8a5a1a', '2x6 wet wall': '#2c6aa0', '2x4 partition': '#b8762a'}
    picks, wall_rows, door_rows, win_rows = {}, [], [], []
    for r in R:
        x0, y0, x1, y1 = (r['a0'], r['c0'], r['a1'], r['c1']) if r['horiz'] else (r['c0'], r['a0'], r['c1'], r['a1'])
        title = f"{r['id']} · {r['type']} · {ft_in(r['len'])}"
        sh.open_group(r['id'], title)
        sh.rect(x0, y0, x1, y1, col[r['type']], 'none', 0, layer='disc', extra=' fill-opacity="0.85"')
        sh.close_group()
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if r['len'] >= 2.5:
            off = 1.1 if r['kind'] == 'E' else 0.0
            tx, ty = (mx, my + (off if r['line'] < 30 else -off)) if r['horiz'] else (mx + (off if r['line'] < 40 else -off), my)
            if r['kind'] == 'E':
                tx, ty = (mx, my - 1.1) if r['horiz'] and r['line'] < 10 else (mx, my + 1.1) if r['horiz'] else (mx - 1.1 if r['line'] < 10 else mx + 1.1, my)
            sh.tag(tx, ty, r['id'][1:], '#8a5a1a' if r['kind'] == 'E' else '#b8762a', r=0.6, size=6.5)
        rooms = ', '.join(ROOMS[n]['name'] if n in ROOMS else 'outside' for n in r['rooms'])
        ops = ', '.join(o['id'] for o in r['openings'])
        st = studs(r)
        notes = []
        if r['garage']: notes.append('garage separation: 5/8" Type X on the garage side, seal penetrations')
        if r['wet']: notes.append('2x6 for 3" drains and vents')
        if r['kind'] == 'E': notes.append('PT bottom plate on the slab, sill gasket, anchor bolts at 6\' o.c. and 12" from ends')
        picks[r['id']] = dict(tag=r['id'], sub=r['type'], fields=[('Length', ft_in(r['len'])), ('Height', f"{ft_in(CEILING)} plate (9' ceilings; vaulted rooms' end walls run to the roof)"),
                                                                ('Between', rooms), ('Openings', ops or 'none'), ('Studs', f'{st} (16" o.c.)'), ('Notes', '; '.join(notes) or '—')])
        wall_rows.append((r['id'], [r['id'], r['type'], ft_in(r['len']), rooms, ops or '—', str(st), '; '.join(notes) or '—']))
    for o in OPENINGS:
        a, (s0, s1) = o['at'], o['span']
        x, y = ((s0 + s1) / 2, a) if o['axis'] == 'y' else (a, (s0 + s1) / 2)
        host = next((r for r in R if o in r['openings']), None)
        ext = bool(host and host['kind'] == 'E') or o.get('ext', False) or o['otype'] == 'window'
        hd = header(o, ext)
        if o['otype'] == 'window':
            rm = ROOMS[o['room']]['name']
            title = f"{o['id']} · window {ft_in(o['w'])} x {ft_in(o['h'])} · {rm}"
            egress = ''
            if ROOMS[o['room']]['kind'] == 'bed' and o['room'] != 'office':
                egress = f"Bedroom: needs 5.7 sf net opening, 20\" clear width, 24\" clear height, sill ≤ 44\" (sill here {ft_in(o['sill'])}{' — too high' if o['sill'] > 44 / 12 else ''})"
            sh.tag(x + (0 if o['axis'] == 'y' else (1.2 if a > 40 else -1.2)), y + ((-1.2 if a < 30 else 1.2) if o['axis'] == 'y' else 0), o['id'][1:], '#2c6aa0', id=o['id'], title=title, r=0.6, size=6)
            fields = [('Room', rm), ('Unit', f"{ft_in(o['w'])} wide x {ft_in(o['h'])} tall (scaled from the elevations)"), ('Rough opening', rough(o)),
                      ('Head / sill', f"{ft_in(o['head'])} / {ft_in(o['sill'])} above slab"), ('Header', hd), ('Wall', host['id'] if host else '—')]
            if egress: fields.append(('Egress', egress))
            picks[o['id']] = dict(tag=o['id'], sub='Window · ' + rm, fields=fields)
            win_rows.append((o['id'], [o['id'], rm, f"{ft_in(o['w'])} x {ft_in(o['h'])}", rough(o), f"{ft_in(o['head'])} / {ft_in(o['sill'])}", hd, egress or '—']))
        else:
            kinds = {'entry': 'exterior entry door', 'french': 'French door pair', 'exterior': 'exterior door', 'overhead': 'overhead garage door', 'fire': '20-min fire-rated, self-closing', 'double': 'door pair',
                     'swing': 'swing door', 'opening': 'cased opening', 'pocket': 'pocket door', 'bypass': 'bypass (sliding) pair'}
            between = ' / '.join(ROOMS[b]['name'] if b in ROOMS else 'outside' for b in o['between'])
            title = f"{o['id']} · {o['name']} · {kinds[o['kind']]} {ft_in(o['w'])}"
            sh.tag(x + (0 if o['axis'] == 'y' else 0.9), y + (0.9 if o['axis'] == 'y' else 0), o['id'], '#6d4c9e', id=o['id'], title=title, r=0.75, size=5.5)
            fields = [('Door', f"{o['name']} ({kinds[o['kind']]})"), ('Between', between), ('Leaf', f"{ft_in(o['w'])} x {ft_in(o['h'])}" + (f", {o.get('leaves')} leaves" if o.get('leaves') else '')),
                      ('Rough opening', rough(o)), ('Header', hd), ('Wall', host['id'] if host else '—')]
            if o['kind'] == 'fire': fields.append(('Code', 'Garage to house: solid wood or steel ≥ 1-3/8", or 20-minute rated, self-closing and self-latching (IRC R302.5.1)'))
            if o['id'] == 'D7': fields.append(('Code', 'Opens from the garage: rate like D6 if the closet counts as part of the house; combustion air per the appliance that goes in'))
            picks[o['id']] = dict(tag=o['id'], sub=o['name'], fields=fields)
            door_rows.append((o['id'], [o['id'], o['name'], kinds[o['kind']], f"{ft_in(o['w'])} x {ft_in(o['h'])}", rough(o), hd, between]))

    # take-offs
    ext = [r for r in R if r['kind'] == 'E']; inte = [r for r in R if r['kind'] == 'I']
    lf = lambda rs: sum(r['len'] for r in rs)
    op_area = lambda rs: sum(o['w'] * o['h'] for r in rs for o in r['openings'] if o.get('kind') != 'overhead')
    ext_lf, int_lf, wet_lf = lf(ext), lf([r for r in inte if not r['wet']]), lf([r for r in inte if r['wet']])
    house_ext = [r for r in ext if 'garage' not in r['rooms']]
    garage_ext = [r for r in ext if 'garage' in r['rooms']]
    wall_board = lf(house_ext) * CEILING - op_area(house_ext) + 2 * (lf(inte) * CEILING) - 2 * op_area(inte)
    heated = [r for r in HOUSE['rooms'] if r['kind'] not in ('garage', 'outdoor')]
    vault = [r for r in heated if r['id'] in ('kitchen', 'living')]
    ceil_flat = sum(r['area_sf'] for r in heated if r not in vault)
    ceil_vault = sum(r['area_sf'] for r in vault) * math.hypot(12, 4) / 12
    wet_board = sum(r['area_sf'] for r in HOUSE['rooms'] if r['kind'] == 'bath') * 0  # shown separately below
    tub_shower_backer = 2 * (5.66 + 2.6) * 6 * 0 + (4 + 6 + 6) * 8 + (5.1 + 3.37 * 2) * 8 + (5.5 + 2.73) * 6   # shower walls to 8', tub surround to 6'
    garage_x = lf([r for r in R if r['garage']]) * CEILING + HOUSE['totals']['garage_sf']
    studs_total = sum(studs(r) for r in R)
    plates = {'2x6': 3 * (ext_lf + wet_lf), '2x4': 3 * int_lf}
    takeoff_rows = [
        (None, ['Exterior wall, 2x6', f'{ext_lf:,.0f} lf', f'{sum(studs(r) for r in ext)} studs 2x6x9\' (104-5/8" precut for 9\' plate)', 'PT 2x6 bottom plate + double top plate']),
        (None, ['Wet walls, 2x6', f'{wet_lf:,.0f} lf', f'{sum(studs(r) for r in inte if r["wet"])} studs 2x6 precut', '']),
        (None, ['Partitions, 2x4', f'{int_lf:,.0f} lf', f'{sum(studs(r) for r in inte if not r["wet"])} studs 2x4 precut', 'PT bottom plate on slab']),
        (None, ['Plates', f"2x6: {plates['2x6']:,.0f} lf · 2x4: {plates['2x4']:,.0f} lf", 'one bottom, two top', 'buy 16\' lengths: ' + f"{math.ceil(plates['2x6'] / 16 * 1.1)} x 2x6, {math.ceil(plates['2x4'] / 16 * 1.1)} x 2x4 (10% waste)"]),
        (None, ['Wall sheathing', f'{(lf(ext) * (CEILING + 1) - op_area(ext)) / 32 * 1.1:,.0f} sheets 7/16" OSB 4x8', 'exterior walls incl. garage, rim to top plate, 10% waste', 'plus housewrap']),
        (None, ['Drywall, walls', f'{wall_board:,.0f} sf · {math.ceil(wall_board / 48 * 1.1)} sheets 1/2" 4x12', 'house walls, both faces of partitions, less openings', '']),
        (None, ['Drywall, ceilings', f'{ceil_flat + ceil_vault:,.0f} sf · {math.ceil((ceil_flat + ceil_vault) / 48 * 1.1)} sheets 5/8" ceiling board 4x12', f'flat {ceil_flat:,.0f} sf + vault {ceil_vault:,.0f} sf (4:12)', '']),
        (None, ['Drywall, garage', f'{garage_x:,.0f} sf · {math.ceil(garage_x / 48 * 1.1)} sheets 5/8" Type X 4x12', 'walls to the house and the ceiling', 'tape and seal for the house separation']),
        (None, ['Tile backer', f'{tub_shower_backer:,.0f} sf cement board', 'two showers to 8\', tub surround to 6\'', 'pedestal tub needs none']),
        (None, ['Studs, total', f'{studs_total:,} pcs', 'kings, jacks and corners included', 'add 10% for blocking and waste']),
    ]
    notes = [
        'Walls are 2x6 exterior and 2x4 interior as drawn on A-1 (5-1/2" and 3-1/2"); wet walls behind toilets, tubs, showers, sinks and the washer go 2x6.',
        'Plate height 9\'-0" (A-2: all interior ceilings 9\' except the 4:12 vault over kitchen and living). Precut studs for a 9\' wall: 104-5/8".',
        'Roof framing is not in the plan set. Trusses bearing on the exterior walls are assumed; with that, interior walls are non-bearing. The vault over kitchen and living needs scissor trusses or a ridge beam: truss designer or engineer to confirm.',
        'Door rough openings: leaf + 2" wide, + 2-1/2" tall. Window rough openings: unit + 1/2" each way (confirm with the window maker).',
        'Headers on exterior walls sized for a single-story truss roof; the two 9\' garage door headers are LVLs to be sized by the engineer or truss/LVL supplier.',
        'Garage separation: 5/8" Type X on the garage side of the walls to the house and on the garage ceiling; D6 is a 20-minute self-closing door.',
        'Blocking: grab bars at every toilet, tub and shower (ADA toilets drawn), towel bars, vanity tops, wall cabinets, TV at the fireplace wall, the curved washer/dryer.',
    ]
    open_items = [
        'Window sizes and heights are scaled from the elevations; confirm the window schedule with the supplier before framing.',
        f"Bedroom 3's only window (W17, 4'x4') scales with a {ft_in(4.0)} sill: above the 44\" egress limit. Lower it or use a casement sized for egress.",
        'Interior door heights are not on the plans (8\'-0" assumed to match the exterior doors on the elevations).',
        'Roof: truss layout, vault framing over kitchen/living and the patio\'s 6:12 vaulted ceiling.',
        'Fireplace insert: chimney chase framing through the vaulted living ceiling and roof; clearances per the insert\'s manual.',
        'Living room label on A-1 says 17\'-4" wide; the walls measure about 20\'-5". Framing follows the walls.',
        'Foundation type (slab assumed: the garage and mechanical floor drains) and anchor schedule.',
    ]
    sh.title_block(['Exterior 2x6 (brown), wet walls 2x6 (blue), partitions 2x4 (tan).', 'Tags: W walls, windows in blue, doors in purple.', 'Roof trusses assumed; interior walls non-bearing.'])
    tables = [
        dict(key='walls', title='Wall schedule', cols=['Wall', 'Type', 'Length', 'Between', 'Openings', 'Studs', 'Notes'], rows=wall_rows),
        dict(key='doors', title='Door schedule', cols=['Door', 'Name', 'Type', 'Leaf', 'Rough opening', 'Header', 'Between'], rows=door_rows),
        dict(key='windows', title='Window schedule', cols=['Window', 'Room', 'Unit', 'Rough opening', 'Head / sill', 'Header', 'Egress'], rows=win_rows),
        dict(key='takeoff', title='Lumber, sheathing and drywall', lede='Rough-order quantities from the wall data, for pricing. The framer takes off the final list.', cols=['Item', 'Quantity', 'Basis', 'Notes'], rows=takeoff_rows),
    ]
    summary = dict(ext_lf=round(ext_lf), int_lf=round(int_lf + wet_lf), studs=studs_total, wall_board=round(wall_board), ceiling_board=round(ceil_flat + ceil_vault), runs=len(R))
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, runs=R)


if __name__ == '__main__':
    b = build()
    print(b['summary'])
    for r in b['runs']:
        print(r['id'], r['type'], round(r['len'], 2), r['rooms'], [o['id'] for o in r['openings']])
