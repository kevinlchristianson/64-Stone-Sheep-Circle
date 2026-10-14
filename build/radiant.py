"""R-1 Radiant: PEX loops on 3" nub boards under the slab, manifolds, zones and flows.

The house heats from its slab: 1/2" PEX laid on EPS25 Super 4 nub boards (4' x 4', 4" of EPS R-18 under a 1"
grid of pucks that hold the tube on a 3" grid), with 4" of concrete over the pucks. Every tube run sits on that 3"
grid, so the whole layout is a walk over a lattice of nodes 3" apart (build/nubgrid.py): a node holds one tube and
nothing can cross. Fields are tube pairs snaking together 6" apart (supply and return side by side, nested bends),
so both ends of a loop sit together at one edge of the panel; from there the leaders are routed node by node to a
manifold port, hugging walls, through doorways and under walls where a gate allows it. Loops stay under 200' with
their leaders. Room loads are M-1's (hvac.room_load); the garage gets its own loops at 6" held at 50°F.

Zoning is by thermostat, not by manifold: every loop has a 24 V actuator on its manifold port, and a thermostat
drives whichever loops are its zone.
"""
import math
from setlib import HOUSE, ROOMS, S, Sheet, px, py
from climate import CLIMATE
import hvac
import plumbing
from nubgrid import P, CLR, Grid, Panel, band_loops, band_path, pair_open, pair_route, verify, corners_ft, node, ft, plen_nodes

MAX_LOOP = 200.0          # ft of 1/2" PEX per loop, leaders included (owner, 2026-10-13)
DT = 10.0                 # design temperature drop per loop, °F
DOWN = 0.07               # share of each loop's heat lost down and out the slab edge, over R-18 boards
R_SLAB = {6: 0.25}        # water to slab surface, h·sf·°F/Btu, 1/2" PEX 6" o.c. in a 4" slab
R_COVER = 0.20            # hard-surface flooring assumed (tile, LVP, engineered wood); carpet is ~1.5
R_SURF = 0.50             # slab surface to room (2.0 Btu/h·sf·°F)
GARAGE_F = 50.0
RISE = 2.0                # ft of leader per end, slab up into the manifold
GARAGE_COLOR = '#2e7d32'
BOARD = dict(name='EPS25 Super 4 nub board', size=4.0, sf=16.0, thick_in=5.0, eps_in=4.0, puck_in=1.0, r=18.0, pitch_in=3.0, per_bundle=5, min_bundles=3,
             url='https://pexuniverse.com/eps25-super-4-foam-insulation')
SLAB_H = -0.39            # tube centre: on the EPS between the pucks, 4-1/2" below the slab top (feet from the slab top)
FEED_H = -0.85            # 1" feed pairs in the base course under the boards
BOARD_Z = (-0.75, -0.333) # the board itself: 5" from the base course to the top of the pucks (4" slab above)

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
STATS = {'T1': (27.6, 16.6), 'T2': (46.0, 41.6), 'T3': (66.5, 39.2), 'TG': (24.2, 40.2)}

# Heat source and the manifold stations. A station hangs on a wall face ('face' is that coordinate along 'axis'; 'side' is
# the room side of it); its loop ends rise out of the slab in one row of 3" ports on the first grid line in front of the
# face, between 'lo' and 'hi' along the wall. 'riser' is where the 1" feed pair comes up to it.
HS = (33.55, 48.8)         # wall-hung on the mechanical closet's east wall (P-1's water manifold and heater share the closet)
T_SUP = 110.0              # design supply cap, °F: keeps a condensing boiler condensing
STATIONS = {
    'MF-1': dict(room='laundry', axis='y', face=18.0, side=+1, lo=18.75, hi=22.0, mount=(2.5, 4.1), riser=(22.6, 18.4),
                 where='Laundry, on the north wall west of the dryer',
                 detail='Surface-mounted manifold cabinet on the laundry\'s north wall, between the linen alcove and the dryer. That wall is the staggered-stud sound wall to the master bed, so the cabinet is not recessed. The master bed, bath and hall loops come under that wall straight up into it; the closet, bath and laundry loops come up from the laundry side.'),
    'MF-2': dict(room='mud', axis='y', face=36.84, side=-1, lo=17.0, hi=18.75, mount=(2.5, 4.1), riser=(19.4, 36.4),
                 where='Mud room, on the south wall (garage wall), west end',
                 detail='Surface-mounted cabinet on the mud room side of the garage wall, back to back with MF-G; the feed pair rises in that wall and serves both.'),
    'MF-G': dict(room='garage', axis='y', face=37.133, side=+1, lo=16.5, hi=24.75, mount=(4.0, 5.6), riser=(19.4, 37.6),
                 where='Garage, on the mud room wall (two 7-loop manifolds side by side)',
                 detail='Surface-mounted cabinets on the garage face of the mud room wall, 4\' above the slab, back to back with MF-2, with the garage\'s own pump P-RG and mixing valve. Surface mounting keeps the garage fire separation whole.'),
    'MF-K': dict(room='mud', axis='x', face=30.54, side=-1, lo=31.75, hi=34.5, mount=(2.5, 4.1), riser=(30.0, 35.2),
                 where='Mud room, east wall (kitchen wall), south of the powder room',
                 detail='Recessed cabinet in the mud room side of the kitchen wall. The kitchen and dining loops come under that wall, under the base cabinets south of the range, straight into it.'),
    'MF-5': dict(room='pantry', axis='x', face=43.707, side=-1, lo=46.75, hi=50.75, mount=(2.5, 4.1), riser=(43.3, 51.2),
                 where='Pantry, on the east wall (entry wall)',
                 detail='Recessed cabinet in the pantry side of the entry wall. The entry, office and living room loops come under that wall straight into it; the pantry loop comes up on the pantry side. Ten feet of 1" feed from HS-1 under the pantry floor.'),
    'MF-3': dict(room='hall', axis='x', face=64.46, side=+1, lo=24.0, hi=28.25, mount=(2.5, 4.1), riser=(64.9, 28.9),
                 where='Bedroom hall, west wall north of the fireplace',
                 detail='Recessed manifold cabinet in the hall\'s west wall between the living room opening and the fireplace chase. A 2x4 wall takes a 3-1/2" deep cabinet; fur it to 2x6 locally if the chosen manifold needs more (S-1).'),
    'MF-4': dict(room='hall', axis='x', face=64.46, side=+1, lo=33.5, hi=36.75, mount=(2.5, 4.1), riser=(64.9, 37.4),
                 where='Bedroom hall, west wall south of the fireplace',
                 detail='Recessed cabinet in the hall\'s west wall south of the fireplace chase, across from the bath 2 door. The living room\'s east loops come under that wall straight into it.'),
}
# tube passes under these stretches of wall (x0, y0, x1, y1 is the wall itself; 'into' names the room on the far side).
# Under a wall a tube only goes straight across; the gates in front of a manifold match its port row, so each tube
# comes up into its own port.
GATES = [
    (18.75, 17.54, 22.0, 18.0, 'laundry'),        # G1 master bed into the laundry, straight into MF-1
    (30.54, 31.75, 30.833, 34.5, 'mud'),          # G4 kitchen into the mud room, under the base cabinets, into MF-K
    (43.707, 46.75, 44.0, 50.75, 'pantry'),       # G3 entry into the pantry, into MF-5
    (64.167, 33.5, 64.46, 36.75, 'hall'),         # G5 living into the hall, into MF-4
    (25.5, 21.833, 27.5, 22.127, 'powder'),       # G6 master hall into the powder room
    (78.25, 15.83, 80.5, 16.13, 'bath1'),         # G7 bedroom 2 closet into bath 1, under the shower floor
]
# nothing passes under these: fixtures with flanges, drains or stub-ups, appliances, the hearth. Tube may pass under the
# kitchen base cabinets (south of the range), the laundry's linen cabinet and the shower floors; the fields keep out of
# every fixture by their own rectangles.
def _fx(kind_ids, grow=0.0):
    out = []
    for f in HOUSE['fixtures']:
        if f['id'] in kind_ids or f['kind'] in kind_ids:
            x, y = f['at']; w, h = f['size']
            out.append((x - w / 2 - grow, y - h / 2 - grow, x + w / 2 + grow, y + h / 2 + grow))
    return out
NO_TUBE = (_fx({'fireplace'}, 0.3) + _fx({'wc'}, 0.25) + _fx({'island', 'range', 'ref', 'tub'}, 0.2)
           + _fx({'K-BACK', 'MB-VAN', 'B2-VAN', 'washer', 'dryer', 'lav'}, 0.1))
DRAINS = [(f['at'][0], f['at'][1], 1.0) for f in HOUSE['fixtures'] if f['kind'] == 'drain']

# Panels: room, rectangle in plan feet, the edge the loop ends sit on ('W', 'E', 'N', 'S'; 'r' starts the bands from the
# other end of that edge), the manifold, and how many 6" rows a band (one loop) may take (0 = whatever 200' allows).
# Rectangles stay 6" off the walls where tube would be near a plate, clear of the cabinets, tubs, vanities, the island,
# the fridge and the hearth, and leave lanes beside the entry edge for the leaders of their own bands and of the loops
# that pass by (those lanes are heated by the leaders).
PANELS = {
    # zone 1, master suite: MF-1
    'MB':  ('master_bed', 16.81, 0.81, 30.19, 15.6, 'Sr', 'MF-1', 10),
    'BA1': ('master_bath', 9.3, 6.0, 13.6, 13.1, 'S', 'MF-1', 0),        # north of the double vanity; leaders down the west side, through the closet and the laundry
    'BA2': ('master_bath', 10.8, 14.9, 15.3, 23.1, 'E', 'MF-1', 0),      # south of the vanity, east of the shower; leaders out through the bedroom door, with a lane east of it for BA1's
    'MC':  ('master_closet', 6.4, 26.5, 15.1, 33.1, 'E', 'MF-1', 0),     # starts below the pocket door's north jamb so the bath 1 leaders get past
    'LA':  ('laundry', 19.9, 20.3, 22.2, 29.3, 'N', 'MF-1', 0),          # between the linen cabinet and the washer / dryer; the lane west of it carries the closet and bath leaders
    'MH':  ('master_hall', 25.4, 18.3, 30.19, 21.5, 'S', 'MF-2', 0),      # its leaders go through the powder room to the mud room
    # zone 2, great room and utility: MF-2, MF-K, MF-5
    'MU1': ('mud', 16.73, 32.0, 24.6, 35.1, 'S', 'MF-2', 0),
    'MU2': ('mud', 27.3, 29.0, 29.8, 41.4, 'S', 'MF-2', 0),               # its leaders leave at the south end and come up the lane by the garage door; the lane west of it carries the hall leaders
    'DI':  ('dining', 32.5, 5.9, 43.35, 15.8, 'W', 'MF-K', 10),
    'KN':  ('kitchen', 33.0, 16.6, 43.35, 22.6, 'W', 'MF-K', 0),          # north of the base cabinets and the island
    'KE':  ('kitchen', 41.3, 23.0, 43.35, 36.3, 'S', 'MF-K', 0),          # east of the island
    'KS':  ('kitchen', 33.6, 37.7, 43.35, 41.6, 'W', 'MF-K', 0),          # south of the island, north of the back cabinet
    'PA':  ('pantry', 34.56, 46.5, 42.9, 52.9, 'E', 'MF-5', 0),               # south of the coat closet's back wall
    'EN':  ('entry', 47.5, 44.0, 49.7, 49.0, 'S', 'MF-5', 0),             # the entry's west side and south end carry leaders
    'LW':  ('living', 44.4, 17.2, 53.9, 41.6, 'S', 'MF-5', 6),
    'LE1': ('living', 53.9, 17.2, 60.2, 42.1, 'E', 'MF-3', 16),            # four bands: two north of the fireplace to MF-3, two south to MF-4
    'LE2': ('living', 60.9, 19.3, 62.8, 26.9, 'S', 'MF-3', 0),            # north of the fireplace; leaders out at its south end, along the hearth and up the wall to the hall opening
    'LE3': ('living', 60.9, 34.8, 63.3, 41.3, 'N', 'MF-4', 0),            # south of the fireplace
    # zone 3, bedroom wing and office: MF-3, MF-4, MF-5
    'OF':  ('office', 52.5, 43.1, 63.8, 52.9, 'W', 'MF-5', 10),
    'B1':  ('bed1', 64.81, 5.9, 77.1, 16.6, 'S', 'MF-3', 12),
    'C2':  ('bed2_closet', 79.2, 17.0, 82.6, 20.8, 'S', 'MF-3', 0),       # one loop with bath 1: out through the closet door, on under the shower floor
    'BT1': ('bath1', 78.3, 6.3, 80.1, 12.0, 'S', 'MF-3', 0),               # the tail of that loop: the open floor west of the lav and toilet, north of the shower
    'B2':  ('bed2', 71.0, 22.4, 82.6, 33.75, 'W', 'MF-3', 12),
    'BT2': ('bath2', 69.5, 34.75, 79.8, 37.3, 'W', 'MF-4', 0),
    'B3':  ('bed3', 64.81, 42.3, 77.1, 52.9, 'N', 'MF-4', 12),
    # garage, 6" like the house (owner, 2026-10-13): MF-G
    'GW':  ('garage', 1.0, 39.5, 5.5, 66.8, 'N', 'MF-G', 4),               # west of the man door line; leaders along the north wall
    'GM':  ('garage', 6.5, 43.5, 13.5, 66.8, 'N', 'MF-G', 6),              # west of the floor drain; the strip under the ports carries its leaders
    'GN':  ('garage', 16.0, 43.5, 20.5, 66.8, 'N', 'MF-G', 6),             # east of the floor drain, under the ports; the rear wall steps back at 15.4
    'GC':  ('garage', 21.8, 39.5, 23.5, 69.2, 'N', 'MF-G', 4),             # straight under the ports
    'GE':  ('garage', 25.5, 45.0, 29.5, 69.2, 'W', 'MF-G', 24),            # east of the mud room; leaders up the lane east of GC
}
# loops that run on into a second panel (open pair through the first, a routed pair connector, closed pair in the second)
CHAINS = [('C2', 'BT1')]
# where the bands of one panel go to different stations
BAND_STATION = {('LE1', 2): 'MF-4', ('LE1', 3): 'MF-4'}
# bands set by hand (6" rows per loop, from the first row): LE1's two north bands keep their lead nodes clear of the
# fireplace chase, which sits beside rows 27.5 to 31.5
BANDS = {'LE1': [14, 16, 10, 10]}
# the order the leaders are routed in: the loop routed first takes the lane along the wall, the next hugs it, so the
# bundles nest. At a port row fed from one side, the loop nearest that end goes first; where bands leave a panel past
# each other toward a gate, the far band goes first and turns off before the near one passes it; where every band
# leaves through the same door, the near band goes first and the far one comes round the outside.
# An entry is a panel, or 'panel.band' for one band of it.
ORDER = ['BA2', 'BA1', 'MC', 'LA', 'MB', 'MU1', 'MU2', 'MH', 'DI', 'KN', 'KS', 'KE', 'PA', 'LW', 'OF.0', 'EN', 'OF.1',
         'LE2', 'LE1.1', 'LE1.0', 'B1', 'C2', 'B2', 'LE3', 'LE1.3', 'LE1.2', 'BT2', 'B3', 'GW', 'GM', 'GN', 'GC', 'GE']
NEAR_FIRST = {'LW', 'B1', 'B3', 'GE'}
# floor a loop's leaders keep off (x0, y0, x1, y1 in feet), so the pair routed first takes the inside of a bundle and
# the ones after it wrap round the outside: LE1's second band stays off the wall side of the lane east of LE2 so the
# first band can come down outside it; the closet loop crosses the hall under the bedroom 2 door before turning north
KEEP_OUT = {'LE1.1': [(63.2, 17.0, 63.6, 20.4)],
            # the three loops that reach MF-3 through the bedroom 2 door turn north at the door, one column further
            # west each, and the first lands on the farthest ports so the others nest inside it
            'C2': [(64.5, 28.5, 67.5, 33.75)], 'B2.0': [(64.5, 28.5, 67.0, 33.75)], 'B2.1': [(64.5, 28.5, 66.5, 33.75)]}
# a loop held to one pair of ports: the coordinate along the port row of its first port (the next one is its second)
PORT = {'BA2': 18.75, 'BA1': 19.75, 'C2': 27.0, 'B2.0': 27.5, 'B2.1': 28.0}


# ---------------------------------------------------------------- the layout
def _line(face, side):
    """The first grid line on the room side of a wall face that keeps tube out of the plate's way."""
    return int(math.ceil((face + 0.2) / P - 1e-9)) if side > 0 else int(math.floor((face - 0.2) / P + 1e-9))


def port_nodes(st):
    k = _line(st['face'], st['side'])
    a, b = int(round(st['lo'] / P)), int(round(st['hi'] / P))
    return [(i, k) for i in range(a, b + 1)] if st['axis'] == 'y' else [(k, j) for j in range(a, b + 1)]


def station_at(st):
    """The middle of the port row, in feet (where the leaders gather up into the cabinet)."""
    k = _line(st['face'], st['side']) * P
    return ((st['lo'] + st['hi']) / 2, k) if st['axis'] == 'y' else (k, (st['lo'] + st['hi']) / 2)


def band_len(panel, v0, n):
    nodes, _, _, _ = band_path(panel, v0, n)
    return plen_nodes(nodes)


def plan_bands(panel, cap, st_at):
    """Split a panel into bands (one loop each) so that a band's tube plus a rough leader fits the loop budget."""
    m, R = panel.local()
    R2 = R - R % 2
    if R2 < 2: return []
    if cap:
        nmax = min(cap, R2)
    else:
        x0, y0, x1, y1 = panel.rect_ft()
        ex, ey = {'W': (x0, (y0 + y1) / 2), 'E': (x1, (y0 + y1) / 2), 'N': ((x0 + x1) / 2, y0), 'S': ((x0 + x1) / 2, y1)}[panel.entry]
        lead = 2 * 1.3 * (abs(ex - st_at[0]) + abs(ey - st_at[1])) + 2 * RISE
        nmax = 2
        for n in range(2, R2 + 1, 2):
            if band_len(panel, 0, n) + lead <= MAX_LOOP - 6: nmax = n
            else: break
    return band_loops(panel, nmax)


def _sub(a, b): return (a[0] - b[0], a[1] - b[1])


def band_rect(panel, v0, n):
    """The floor one band of a panel heats, in feet: its tube extents plus half a spacing all round."""
    s = panel.s
    a = panel.to_node(0, v0); b = panel.to_node(panel.local()[0] - 1, v0 + (n - 1) * s)
    x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
    h = s * P / 2
    return (x0 * P - h, y0 * P - h, x1 * P + h, y1 * P + h)


def layout(caps=None, first=(), verbose=False, stop_before=None):
    """Lay every loop out on the grid. Returns the loops (fields, leaders, lengths), the grid and a list of failures."""
    caps = dict(caps or {})
    grid = Grid(HOUSE, gates=GATES, no_tube=NO_TUBE, drains=DRAINS)
    panels = {k: Panel(v[0], v[1], v[2], v[3], v[4], v[5]) for k, v in PANELS.items()}
    for pn in panels.values():
        grid.field.update(pn.bbox_nodes())
    for k, st in STATIONS.items():
        grid.add_ports(k, port_nodes(st), st['room'])
    chained = {b: a for a, b in CHAINS}
    loops = []
    for k, v in PANELS.items():
        if k in chained: continue
        pn = panels[k]; st = v[6]
        if k in BANDS and k not in caps:
            bands = []; vv = 0
            for n in BANDS[k]: bands.append((vv, n)); vv += n * pn.s
        else:
            bands = plan_bands(pn, caps.get(k, v[7]), station_at(STATIONS[st]))
        for bi, (v0, n) in enumerate(bands):
            st_b = BAND_STATION.get((k, bi), st)
            tail = next((b for a, b in CHAINS if a == k), None)
            if tail:
                if n % 4 == 0: n -= 2          # an open pair must end at the far edge
                if n < 2: continue
                na, nb, lin, lout, ends = pair_open(pn, v0, n)
                pb = panels[tail]
                m2, R2 = pb.local(); n2 = R2 - R2 % 2
                nodes2, _, lin2, lout2 = band_path(pb, 0, n2)
                loops.append(dict(panel=k, band=bi, st=st_b, room=v[0], a=na, b=nb, lead_in=lin, lead_out=lout, ends=ends, n=n,
                                  tail=tail, field2=nodes2, lead_in2=lin2, lead_out2=lout2, panels=[pn, pb], rooms=[v[0], PANELS[tail][0]],
                                  rects=[band_rect(pn, v0, n), band_rect(pb, 0, n2)]))
            else:
                nodes, corners, lin, lout = band_path(pn, v0, n)
                loops.append(dict(panel=k, band=bi, st=st_b, room=v[0], field=nodes, lead_in=lin, lead_out=lout, panels=[pn], rooms=[v[0]], n=n,
                                  rects=[band_rect(pn, v0, n)]))
    # fields and the lead nodes go down first; leaders thread between them afterwards
    bad = []
    for i, l in enumerate(loops):
        l['tag'] = f'L{i + 1}'
        if 'field' in l:
            grid.take(l['field'], l['tag'] + 'f')
        else:
            grid.take(l['a'], l['tag'] + 'a'); grid.take(l['b'], l['tag'] + 'b'); grid.take(l['field2'], l['tag'] + 'f')
            grid.used[l['ends'][0]] = l['tag'] + 'c1'; grid.used[l['ends'][1]] = l['tag'] + 'c2'
            grid.used[l['lead_in2']] = l['tag'] + 'c1'; grid.used[l['lead_out2']] = l['tag'] + 'c2'
        grid.used[l['lead_in']] = l['tag'] + 's'; grid.used[l['lead_out']] = l['tag'] + 'r'
        hit = [n for n in (l.get('field') or l['a'] + l['b'] + l['field2']) if n in grid.blocked or n not in grid.room]
        if hit: bad.append(f"{l['tag']} {l['panel']}: field over a wall, fixture or drain at {[ft(n) for n in hit[:3]]}")
    if bad: raise ValueError('; '.join(bad))
    fails = []
    # connectors of the chained loops: the pair runs on from the two open ends to the second panel's lead nodes
    for l in loops:
        if 'tail' not in l: continue
        e0, e1 = l['ends']; t1, t2 = l['tag'] + 'c1', l['tag'] + 'c2'
        r = pair_route(grid, e0, e1, _sub(e0, l['a'][-1]), leads=(l['lead_in2'], l['lead_out2']))
        if not r:
            fails.append((l['tag'], l['panel'], 'connector')); l['conn'] = None
            continue
        ca, cb = r
        grid.take(ca, t1); grid.take(cb, t2)
        # tube A runs on from end 0; if its connector lands on lead_out2 the second panel is run the other way round
        if ca[-1] == l['lead_out2']: l['field2'] = l['field2'][::-1]
        l['conn'] = (ca, cb)
    # leaders, farthest loops first (they take the outside lanes), with any hand-picked ones before them
    def far(l):
        sx, sy = station_at(STATIONS[l['st']]); x, y = ft(l['lead_in'])
        return abs(x - sx) + abs(y - sy)
    def rank(l):
        k = l['panel']; kb = f"{k}.{l['band']}"
        if k in first: return (0, first.index(k), 0)
        if kb in ORDER: return (1, ORDER.index(kb), 0)
        return (1, ORDER.index(k) if k in ORDER else 99, far(l) * (1 if k in NEAR_FIRST else -1))
    order = sorted(loops, key=rank)
    for l in order:
        st = l['st']
        kb = f"{l['panel']}.{l['band']}"
        if stop_before and kb == stop_before: break
        d0 = _sub(l['lead_in'], l['field'][0] if 'field' in l else l['a'][0])
        grid.keep_out = set()
        for x0, y0, x1, y1 in KEEP_OUT.get(kb, KEEP_OUT.get(l['panel'], [])):
            grid.keep_out.update((i, j) for i in range(int(x0 / P), int(x1 / P) + 2) for j in range(int(y0 / P), int(y1 / P) + 2)
                                 if x0 - 1e-6 <= i * P <= x1 + 1e-6 and y0 - 1e-6 <= j * P <= y1 + 1e-6)
        pl = grid.ports[st]
        if kb in PORT or l['panel'] in PORT:
            c = int(round(PORT.get(kb, PORT.get(l['panel'])) / P)); ax = 0 if STATIONS[st]['axis'] == 'y' else 1
            pl = [n for n in pl if n[ax] in (c, c + 1)]
        r = pair_route(grid, l['lead_in'], l['lead_out'], d0, ports=pl)
        grid.keep_out = set()
        if r:
            ps, pr = r
            grid.take(ps, l['tag'] + 's'); grid.take(pr, l['tag'] + 'r')
            l['sup'], l['ret'] = ps, pr
        else:
            l['sup'] = l['ret'] = None
            fails.append((l['tag'], l['panel'], 'leader'))
            if verbose: print('FAIL', l['tag'], l['panel'], st)
    # lengths and the tube as drawn
    for l in loops:
        tube = []
        if l.get('sup'): tube += l['sup'][::-1]
        if 'field' in l:
            tube += l['field']
        else:
            tube += l['a']
            if l.get('conn'):
                tube += l['conn'][0] + l['field2'] + l['conn'][1][::-1]
            tube += l['b'][::-1]
        if l.get('ret'): tube += l['ret']
        l['tube'] = tube
        l['in_floor'] = plen_nodes(l['field']) if 'field' in l else plen_nodes(l['a']) + plen_nodes(l['b']) + plen_nodes(l['field2']) + (plen_nodes(l['conn'][0]) + plen_nodes(l['conn'][1]) if l.get('conn') else 0)
        l['leader'] = (plen_nodes(l['sup']) if l.get('sup') else 0) + (plen_nodes(l['ret']) if l.get('ret') else 0) + 2 * RISE
        l['total'] = l['in_floor'] + l['leader'] + (2 * P if l.get('sup') else 0) + (2 * P if l.get('ret') else 0)   # the steps from lead nodes into the field
        l['ports'] = (l['sup'][-1], l['ret'][-1]) if l.get('sup') and l.get('ret') else None
    return loops, grid, fails


def solve(verbose=False):
    """Lay out, then trim any band whose loop came out over budget, and put loops that could not be routed first."""
    caps = {}; first = []
    for it in range(14):
        loops, grid, fails = layout(caps, first, verbose)
        over = [l for l in loops if l['total'] > MAX_LOOP]
        if verbose:
            print(f"pass {it}: {len(loops)} loops, {len(fails)} failures, {len(over)} over {MAX_LOOP:.0f}'")
        if not fails and not over: return loops, grid
        for tag, panel, what in fails:
            if panel not in first: first.append(panel)
        for l in over:
            caps[l['panel']] = max(2, min(caps.get(l['panel'], 99), l['n'] - 2))
    raise RuntimeError(f'radiant layout did not settle: failures {fails}, over budget {[l["tag"] for l in over]}')


# ---------------------------------------------------------------- hydronics
def lc(t): return t[:1].lower() + t[1:]


def head_ft(L, gpm): return L * 0.0118 * (gpm / 0.5) ** 1.75


def plen(pts): return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))


def room_loads():
    out = {}
    for r in HOUSE['rooms']:
        if r['kind'] == 'outdoor': continue
        h = hvac.room_load(r)['heat']
        if r['kind'] == 'garage':
            h *= (GARAGE_F - CLIMATE['heat_design_f']) / (CLIMATE['indoor_heat_f'] - CLIMATE['heat_design_f'])
        out[r['id']] = h
    return out


# the 1" feed pairs from HS-1 to the stations, under the boards. Three share the run under the kitchen's west base cabinets,
# two the run under the entry and office; each is drawn a few inches from the next so they read apart.
FEED_ROUTES = {
    'MF-1': [HS, (31.6, HS[1]), (31.6, 18.4), STATIONS['MF-1']['riser']],
    'MF-2': [HS, (32.0, HS[1]), (32.0, 36.4), STATIONS['MF-2']['riser']],
    'MF-K': [HS, (32.4, HS[1]), (32.4, 35.2), STATIONS['MF-K']['riser']],
    'MF-5': [HS, (43.3, HS[1]), STATIONS['MF-5']['riser']],
    'MF-4': [HS, (HS[0], 44.5), (64.9, 44.5), STATIONS['MF-4']['riser']],
    'MF-3': [HS, (HS[0] - 0.3, HS[1]), (HS[0] - 0.3, 44.8), (65.2, 44.8), (65.2, 28.9), STATIONS['MF-3']['riser']],
}


def hydronics(loops, grid):
    """Each loop's heat, flow, head and water temperature, and the feed pairs. A room's M-1 load is carried by all the tube in
    it, fields and the leaders passing through alike, shared by length; the floor a room's tube heats is half a square foot per
    foot of tube (6" spacing), up to the room's area, and that sets the water it needs."""
    loads = room_loads()
    tube_in = {}
    for l in loops:
        cnt = {}
        for n in l['tube']:
            r = grid.room.get(n)
            if r: cnt[r] = cnt.get(r, 0) + 1
        l['ft_in'] = {r: c * P for r, c in cnt.items()}
        for r, f in l['ft_in'].items(): tube_in[r] = tube_in.get(r, 0.0) + f
    heated = {r: min(ROOMS[r]['area_sf'], f * 0.5) for r, f in tube_in.items()}
    for l in loops:
        z = ZONE_OF[l['rooms'][0]]; l['zone'] = z; l['id'] = l['tag']
        shares = {r: f / tube_in[r] for r, f in l['ft_in'].items()}
        q_room = sum(loads[r] * sh for r, sh in shares.items())
        area = sum(heated[r] * sh for r, sh in shares.items())
        t_room = GARAGE_F if z == 'ZG' else CLIMATE['indoor_heat_f']
        r_tot = R_SLAB[6] + (0.0 if z == 'ZG' else R_COVER) + R_SURF
        # the water the loop needs is set by the room it heats most that needs the most (a doorway it passes through does not count)
        main = [r for r in shares if l['ft_in'][r] >= 10 or r in l['rooms']]
        flux = max(loads[r] / heated[r] for r in main)
        short = sum(max(0.0, loads[r] - heated[r] * (T_SUP - DT / 2 - t_room) / r_tot) * shares[r] for r in main) if z != 'ZG' else 0.0
        l.update(area=area, q_room=q_room, q=q_room * (1 + DOWN), t_avg=t_room + flux * r_tot, t_surf=t_room + flux * R_SURF, short=short,
                 room_names=[ROOMS[r]['name'] for r in l['rooms']], heats=[ROOMS[r]['name'] for r in sorted(shares, key=lambda r: -l['ft_in'][r]) if l['ft_in'][r] >= 10])
        l['gpm'] = max(0.2, l['q'] / (500 * DT)); l['head'] = head_ft(l['total'], l['gpm'])
    unheated = [(r['id'], r['name'], loads[r['id']]) for r in HOUSE['rooms'] if r['kind'] != 'outdoor' and r['id'] not in tube_in]
    by_leaders = [(r['id'], r['name'], loads[r['id']], tube_in[r['id']]) for r in HOUSE['rooms'] if r['kind'] != 'outdoor' and r['id'] in tube_in and r['id'] not in {rm for l in loops for rm in l['rooms']}]
    feeds = []
    for k, pts in FEED_ROUTES.items():
        on = [k, 'MF-G'] if k == 'MF-2' else [k]
        feeds.append(dict(id='F-' + k[3:], mf=k, to='MF-2 and MF-G' if k == 'MF-2' else k, pts=pts, lf=plen(pts), gpm=sum(l['gpm'] for l in loops if l['st'] in on)))
    return loads, unheated, by_leaders, feeds


def coils(lengths, coil=1000.0):
    """How many coils the loops cut from, one uncut length per loop, longest first into whichever coil has room."""
    left = []
    for L in sorted(lengths, reverse=True):
        for i, r in enumerate(left):
            if r >= L: left[i] -= L; break
        else: left.append(coil - L)
    return len(left)


# ---------------------------------------------------------------- the sheet
def draw_boards(sh):
    """The boards under the slab, on the rooms layer: 4' x 4' in a running bond from the datum, with their 3" nub grid as the
    dot pattern (a dot is a puck; tube runs between the dots), clipped to the slab."""
    clip = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in plumbing.OUTLINE)
    tile = P * S
    sh.add(f'<defs><clipPath id="r1-slab"><polygon points="{clip}"/></clipPath>'
           f'<pattern id="r1-nubs" patternUnits="userSpaceOnUse" x="{px(0):.1f}" y="{py(0):.1f}" width="{tile:.3f}" height="{tile:.3f}">'
           f'<circle cx="{tile / 2:.3f}" cy="{tile / 2:.3f}" r="0.38" fill="#aaa399"/></pattern></defs>', 'rooms')
    xs = [p[0] for p in plumbing.OUTLINE]; ys = [p[1] for p in plumbing.OUTLINE]
    B = BOARD['size']
    out = [f'<g clip-path="url(#r1-slab)"><polygon points="{clip}" fill="url(#r1-nubs)"/>']
    for k in range(int(min(ys) // B), int(max(ys) // B) + 1):
        y0 = k * B; y1 = y0 + B
        out.append(f'<line x1="{px(min(xs)):.1f}" y1="{py(y0):.1f}" x2="{px(max(xs)):.1f}" y2="{py(y0):.1f}" stroke="#bdb6aa" stroke-width="0.7"/>')
        off = B / 2 if k % 2 else 0.0
        for j in range(int(min(xs) // B) - 1, int(max(xs) // B) + 2):
            x = j * B + off
            out.append(f'<line x1="{px(x):.1f}" y1="{py(y0):.1f}" x2="{px(x):.1f}" y2="{py(y1):.1f}" stroke="#bdb6aa" stroke-width="0.7"/>')
    out.append('</g>')
    sh.add(''.join(out), 'rooms')


def station_box(st, grow=0.25, depth=0.35, into_wall=0.0):
    """A manifold cabinet on the plan: along the wall over its port row, `depth` into the room (and `into_wall` the other way)."""
    lo, hi = st['lo'] - grow, st['hi'] + grow
    f, sd = st['face'], st['side']
    if st['axis'] == 'y': return (lo, min(f - sd * into_wall, f + sd * depth), hi, max(f - sd * into_wall, f + sd * depth))
    return (min(f - sd * into_wall, f + sd * depth), lo, max(f - sd * into_wall, f + sd * depth), hi)


def build():
    sh = Sheet('R-1', 'Radiant floor', f"PEX loops on 3\" nub boards under the slab: {MAX_LOOP:.0f}' loops, nothing crossing, seven manifolds, four thermostat zones, flows at {CLIMATE['name']} design ({CLIMATE['heat_design_f']:.0f}°F).")
    sh.base()
    draw_boards(sh)
    loops, grid = solve()
    verify(grid, [(l['tag'], l['tube']) for l in loops])
    loads, unheated, by_leaders, feeds = hydronics(loops, grid)
    t_supply = min(T_SUP, math.ceil((max(l['t_avg'] for l in loops if l['zone'] != 'ZG') + DT / 2) / 5) * 5)
    shorts = [l for l in loops if l['short'] > 300]
    by_st = {k: [l for l in loops if l['st'] == k] for k in STATIONS}
    def port_no(l):
        row = grid.ports[l['st']]
        return tuple(row.index(n) + 1 for n in l['ports'])
    picks = {}
    for l in loops:
        z = l['zone']; Z = ZONES[z]; c = Z['color']; st = l['st']; ps, pr = port_no(l)
        rooms = ', '.join(l['room_names'])
        title = (f"Loop {l['id']}, zone {z[1:]} ({Z['name']}): {rooms}. {l['in_floor']:.0f}' in the field + {l['leader']:.0f}' of leaders = {l['total']:.0f}' of 1/2\" PEX at 6\" o.c., "
                 f"to {st} ports {ps} and {pr}. {l['q']:,.0f} Btu/h, {l['gpm']:.2f} gpm on the flow meter, {l['head']:.1f} ft of head. One continuous coil, no fittings in the slab; tag both ends {l['id']}.")
        sh.open_group(l['id'], title)
        tube = l['tube']; ns, nr = len(l['sup']), len(l['ret'])
        sh.path(corners_ft(tube), 'transparent', 7)
        sh.path(corners_ft(tube[ns - 1:len(tube) - nr + 1]), c, 1.1, extra=' class="pex"')
        sh.path(corners_ft(l['sup']), c, 0.9, '4,1.2', extra=' class="lead"'); sh.path(corners_ft(l['ret']), c, 0.9, '4,1.2', extra=' class="lead"')
        x0, y0, x1, y1 = max(l['rects'], key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        sh.add(f'<text x="{px((x0 + x1) / 2):.1f}" y="{py((y0 + y1) / 2 + (1.4 if y1 - y0 > 4 else 0)):.1f}" font-size="7.5" font-weight="700" fill="{c}" text-anchor="middle" dominant-baseline="middle" stroke="#fff" stroke-width="2.5" paint-order="stroke">{l["id"]}</text>')
        sh.close_group()
        picks[l['id']] = dict(tag=l['id'], sub=f"Zone {z[1:]} · {Z['name']}", fields=[
            ('Rooms', rooms + (f" (its leaders also heat {', '.join(h for h in l['heats'] if h not in l['room_names'])})" if [h for h in l['heats'] if h not in l['room_names']] else '')), ('Tube', f"{l['total']:.0f}' of 1/2\" PEX: {l['in_floor']:.0f}' in the field at 6\" o.c. + {l['leader']:.0f}' of leaders (both ends, with the 2' rises)"),
            ('Manifold', f"{st}, ports {ps} (supply) and {pr} (return), {lc(STATIONS[st]['where'])}"), ('Heat', f"{l['q']:,.0f} Btu/h at design, {l['area']:.0f} sq ft of heated floor"),
            ('Flow', f"{l['gpm']:.2f} gpm on the flow meter, {l['head']:.1f} ft of head in the tube"),
            ('Water / floor', f"needs about {l['t_avg']:.0f}°F average water; floor surface about {l['t_surf']:.0f}°F at design"),
            ('Thermostat', f"{Z['stat']}, actuator on {st} port {pr}")])
    for f in feeds:
        sh.open_group(f['id'], f"1\" PEX supply and return pair, HS-1 to {f['to']}: about {f['lf']:.0f}' each way, {f['gpm']:.1f} gpm, under the boards, insulated end to end.")
        sh.path(f['pts'], 'transparent', 7); sh.path(f['pts'], '#6a1b9a', 3.0); sh.path(f['pts'], '#fff', 1.0)
        sh.close_group()
        picks[f['id']] = dict(tag=f['id'], sub=f"Feed pair to {f['to']}", fields=[('Pipe', '1" PEX supply + return, closed-cell insulated end to end, in the base course under the nub boards'),
                                                                                ('Run', f"about {f['lf']:.0f}' each way from HS-1"), ('Flow', f"{f['gpm']:.1f} gpm with every loop on {f['to']} calling")])
    for k, st in STATIONS.items():
        on = by_st[k]; n = len(on); nports = len(grid.ports[k])
        x, y = station_at(st)
        title = f"{k}: {n}-loop stainless manifold with flow meters and 24 V actuators, {lc(st['where'])}. {st['detail']}"
        sh.open_group(k, title, hit=(x, y, 1.4))
        bx = station_box(st, into_wall=0.25)
        sh.rect(bx[0], bx[1], bx[2], bx[3], '#fff', '#222', 1.3, '4,2')
        horiz = st['axis'] == 'y'
        sh.text((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, k, 6.5, '#222', '700', rot=0 if horiz else -90, layer='disc')
        sh.close_group()
        picks[k] = dict(tag=k, sub=st['where'], fields=[
            ('Manifold', f"{n}-loop stainless, flow meters, isolation ball valves, purge/fill and a 24 V actuator on every return port" + (' (two manifolds side by side)' if n > 8 else '')),
            ('Loops', ', '.join(f"{l['id']} on {'/'.join(str(p) for p in port_no(l))}" for l in on) + f"; {2 * n} of {nports} 3\" port positions used"),
            ('Flow', f"{sum(l['gpm'] for l in on):.1f} gpm with all loops calling"), ('Where', st['detail'])])
    x, y = HS
    sh.open_group('HS-1', 'HS-1, condensing boiler for the slab, with the system pump, mixing and the zone controller', hit=(x, y, 1.2))
    sh.rect(x - 1.1, y - 0.6, x + 1.1, y + 0.6, '#fff', '#6a1b9a', 1.6); sh.text(x, y, 'HS-1', 6, '#6a1b9a', '700', layer='disc')
    sh.close_group()
    tot_q = sum(l['q'] for l in loops); house_q = sum(l['q'] for l in loops if l['zone'] != 'ZG'); tot_gpm = sum(l['gpm'] for l in loops)
    picks['HS-1'] = dict(tag='HS-1', sub='Mechanical closet', fields=[
        ('Equipment', "Wall-hung condensing boiler with outdoor reset, on natural gas or propane (owner's picks, 2026-10-13); circuit 27 on E-1"),
        ('Output', f"{tot_q:,.0f} Btu/h with every zone calling, {house_q:,.0f} Btu/h for the house alone"),
        ('Water', f"{t_supply:.0f}°F supply at {CLIMATE['heat_design_f']:.0f}°F outside, reset down to about 80°F at 50°F outside; garage loops mix down to about 70°F"),
        ('Pumps', 'P-R1: ECM circulator on constant ΔP for the six house manifolds; P-RG for MF-G on its own mixing valve'),
        ('Controls', '24 V zone controller with T1, T2, T3 and TG; outdoor sensor on the shaded rear wall')])
    for z, Z in ZONES.items():
        x, y = STATS[Z['stat']]
        sh.tag(x, y, Z['stat'], Z['color'], id=Z['stat'], title=f"{Z['stat']}, zone {z[1:]} thermostat ({Z['name']}): {Z['where']}.", r=0.62, size=6)
        lz = [l for l in loops if l['zone'] == z]
        picks[Z['stat']] = dict(tag=Z['stat'], sub=f"Zone {z[1:]} · {Z['name']}", fields=[('Where', Z['where']), ('Loops', ', '.join(l['id'] for l in lz)),
                                                                                       ('Manifolds', ', '.join(sorted({l['st'] for l in lz}))), ('Load', f"{sum(l['q'] for l in lz):,.0f} Btu/h at design")])
    legend = [(Z['color'], f"Zone {z[1:]}, {Z['name']} ({Z['stat']})") for z, Z in ZONES.items()] + [('#6a1b9a', '1" feed pair from HS-1, under the boards')]
    sym = [(f'<line x1="-12" y1="0" x2="12" y2="0" stroke="{c}" stroke-width="1.6"/>', t) for c, t in legend[:-1]]
    sym += [('<line x1="-12" y1="0" x2="12" y2="0" stroke="#555" stroke-width="1" stroke-dasharray="4,1.2"/>', 'leaders, supply and return side by side 3" apart'),
            ('<line x1="-12" y1="0" x2="12" y2="0" stroke="#6a1b9a" stroke-width="3"/><line x1="-12" y1="0" x2="12" y2="0" stroke="#fff" stroke-width="1"/>', legend[-1][1]),
            ('<rect x="-9" y="-4" width="18" height="8" fill="#fff" stroke="#222" stroke-dasharray="3,2"/>', 'manifold cabinet over its row of 3" ports'),
            ('<rect x="-10" y="-6" width="20" height="12" fill="#fff" stroke="#bdb6aa"/><line x1="0" y1="-6" x2="0" y2="6" stroke="#bdb6aa"/>' + ''.join(f'<circle cx="{cx}" cy="{cy}" r="0.5" fill="#aaa399"/>' for cx in (-7.5, -5, -2.5, 2.5, 5, 7.5) for cy in (-3.5, -1, 1.5, 4)), "4' x 4' nub boards in a running bond from the datum; dots are the 3\" puck grid")]
    sh.legend(sym)
    # numbers for the notes and tables
    tot_tube = sum(l['total'] for l in loops); leaders = sum(l['leader'] for l in loops)
    longest = max(loops, key=lambda l: l['total']); shortest = min(loops, key=lambda l: l['total'])
    worst = max(loops, key=lambda l: l['head'])
    feed_lf = sum(f['lf'] for f in feeds)
    slab_sf = HOUSE['totals']['heated_gross_sf'] + HOUSE['totals']['garage_gross_sf']
    boards = math.ceil(slab_sf / BOARD['sf'] * 1.05); bundles = max(BOARD['min_bundles'], math.ceil(boards / BOARD['per_bundle']))
    n_coils = coils([l['total'] * 1.02 for l in loops])
    unheated_txt = ', '.join(f"{nm} ({q:,.0f} Btu/h)" for _, nm, q in unheated)
    leaders_txt = ', '.join(f"{nm} ({ft:.0f}' of leaders for {q:,.0f} Btu/h)" for _, nm, q, ft in by_leaders)
    gates_txt = 'under the master bed wall into MF-1, under the kitchen wall into MF-K, under the entry wall into MF-5, under the living room wall into MF-4, under the master hall wall into the powder room, and under the bath 1 wall from the bedroom 2 closet'
    station_txt = '; '.join(f"{k} ({lc(STATIONS[k]['where'])}, {len(by_st[k])} loops) serves " + ', '.join(sorted({r for l in by_st[k] for r in l['room_names']}, key=lambda n: [r['name'] for r in HOUSE['rooms']].index(n))) for k in STATIONS)
    notes = [
        f"The layout is drawn on the boards' own grid. {BOARD['name']}s ({BOARD['size']:.0f}' x {BOARD['size']:.0f}', {BOARD['thick_in']:.0f}\" thick: {BOARD['eps_in']:.0f}\" of EPS, R-{BOARD['r']:.0f}, under a {BOARD['puck_in']:.0f}\" grid of pucks on {BOARD['pitch_in']:.0f}\" centres) go down in a running bond with their puck rows on the 3\" lines from the datum at 0,0 (the garage-door wall's outside face and the master bed's rear wall line, as on every sheet), so every tube on this sheet sits in a channel between pucks. Lay the first board's corner at the datum and the rest follow; a board cut at a wall keeps its grid.",
        f"Tube: {len(loops)} loops of 1/2\" O2-barrier PEX, none over {MAX_LOOP:.0f}' with its leaders and the 2' rises at the cabinet ({longest['id']} is the longest at {longest['total']:.0f}', {shortest['id']} the shortest at {shortest['total']:.0f}'). Fields at 6\" o.c. (every other channel), supply and return side by side so each loop's two ends leave its field together; leaders run as 3\" pairs through doorways and along walls to their manifold. Nothing crosses anything: the whole layout was checked tube by tube on the grid. One continuous coil per loop, no fittings in the slab; tag both ends with the loop number at the cabinet.",
        f"Under a wall only where drawn, straight across and only for the length drawn: {gates_txt}. Mark every wall crossing on the boards before the pour so the plate anchors and shots stay 12\" off it; everywhere else the leaders go through the doorway.",
        f"Nothing under the kitchen base cabinets' footprint except the leaders drawn there, nor under the island, fridge, back cabinet, range, washer, dryer, tubs, vanities or the fireplace hearth. 12\" clear of the floor drains and shower drains, 3\" of a toilet flange; the showers' floors are heated. The bathroom loops heat the open floor; the closets and halls get their heat from the leaders passing through, and the laundry has a small field of its own.",
        f"Manifolds, seven stations, each with a 3\" port position per tube end in one row along its wall (the schedule gives every loop's two port numbers, counted from the low end of the row): {station_txt}. HS-1 in the mechanical closet feeds all seven on six 1\" insulated pairs under the boards, {feed_lf:.0f}' each way in all; MF-2 and MF-G share one pair rising in the garage wall.",
        f"The leaders rise straight up out of the slab at their port positions into the cabinet (sleeve each rise in 12\" of pipe insulation where it leaves the concrete) and bundle up to the manifold; they may be gathered sideways in the last 12\" below the cabinet. Cabinets are recessed in the kitchen and entry walls (MF-K, MF-5) and the hall wall (MF-3, MF-4) and surface-mounted on the laundry's sound wall (MF-1) and both faces of the garage wall (MF-2, MF-G).",
        f"Zoning is by thermostat: four zones (master suite, great room and utility, bedroom wing and office, garage) on 24 V actuators at each loop's manifold port, so a room can get its own thermostat later by rewiring, without new tube.",
        f"Flow: {tot_gpm:.1f} gpm with every loop calling, each loop set on its flow meter at a {DT:.0f}°F drop. Design heat {tot_q:,.0f} Btu/h, of which {tot_q - house_q:,.0f} is the garage at {GARAGE_F:.0f}°F; {DOWN * 100:.0f}% is added for heat lost down through the R-{BOARD['r']:.0f} boards and out the slab edge. Rooms with no field of their own are heated by the leader bundles running through them: {leaders_txt}. Nothing heats the {unheated_txt}; they borrow from the rooms around them.",
        f"Water: {t_supply:.0f}°F supply at {CLIMATE['heat_design_f']:.0f}°F outside, reset lower as it warms, so a condensing boiler stays condensing. Floor surfaces stay at or under {max(l['t_surf'] for l in loops if l['zone'] != 'ZG'):.0f}°F."
        + (' At that supply ' + ', '.join(f"{l['id']} ({', '.join(l['room_names'])}) falls about {l['short']:,.0f} Btu/h short" for l in shorts) + ' at design; see the open items.' if shorts else ''),
        f"Pump: the hardest loop is {worst['id']} at {worst['head']:.1f} ft in the tube; add about 3 ft for the feed pair, manifold and actuator. A constant-ΔP ECM circulator at about {math.ceil(worst['head'] + 3)} ft covers the house; the garage has its own.",
        f"Under the boards: 10-mil vapor barrier over the compacted base, lapped and taped; R-10 (2\") rigid foam at the slab edge. The 4\" slab goes over the pucks with the tube tops about 1\" below the surface of the boards; no mesh ties are needed, the pucks hold the tube. Pressure test every loop at 100 psi water or 60 psi air for 24 hours before the pour and keep it under pressure through the pour. Photograph every room with a tape in frame before concrete.",
        'HS-1 is circuit 27 on E-1 (200 A panel in the garage); E-1 also gives each manifold cabinet an outlet for its actuators and the zone controller.',
    ]
    open_items = [f"{l['id']} ({', '.join(l['room_names'])}): the floor carries all but about {l['short']:,.0f} Btu/h of the room at {CLIMATE['heat_design_f']:.0f}°F with {T_SUP:.0f}°F water. Add a small electric towel warmer, or run the boiler hotter on the coldest days." for l in shorts] + [
        "Boiler model: HS-1 is a condensing boiler on natural gas or propane (decided 2026-10-13). Pick a combi or a boiler with an indirect tank if it should also make the domestic hot water and replace P-1's 50 gal heater; propane needs the boiler's LP conversion kit.",
        'Garage: kept at 50°F on its own manifold, pump and thermostat. Decide whether it runs a glycol mix behind a plate heat exchanger, which protects it if the house loses power in a cold snap with the doors open.',
        'Flooring: the loops assume hard-surface floors. Carpet in a bedroom needs about 10°F warmer water for that loop.',
        "P-1's hot and cold PEX runs at 6.5\" to 8\" below the slab top, which is now inside the 5\" board layer. Either drop them into the base course under the boards (about 10\" down) or cut channels in the EPS for them; P-1 to pick.",
        "Cabinet depths on S-1: MF-3 and MF-4 recess into the hall's 2x4 west wall (3-1/2\" deep; fur locally if the chosen manifold needs more), MF-K into the kitchen wall and MF-5 into the entry wall.",
        f"E-1: an outlet at each of the seven manifold cabinets for the actuators (MF-1, MF-2, MF-G, MF-K, MF-5, MF-3, MF-4), and the boiler, pump and zone controller on circuit 27.",
        f"The {BOARD['name']}s come {BOARD['per_bundle']} to a bundle ({BOARD['per_bundle'] * BOARD['sf']:.0f} sq ft), {BOARD['min_bundles']} bundles minimum: {bundles} bundles cover the {slab_sf:,} sq ft slab with 5% for cuts. Confirm the lead time; the board layout can start at any corner as long as the grid holds the datum.",
    ]
    sh.title_block([f"{len(loops)} loops, {tot_tube:,.0f}' of 1/2\" PEX, {len(STATIONS)} manifolds, no loop over {MAX_LOOP:.0f}'.", 'Red zone 1, orange zone 2, blue zone 3, green garage.',
                    f"{tot_q / 1000:,.0f} kBtu/h at design, {t_supply:.0f}°F supply.", f"{BOARD['name']}s on the 3\" grid from the datum; nothing crosses."])
    loop_rows = [(l['id'], [l['id'], l['zone'][1:], ', '.join(l['room_names']), l['st'], '/'.join(str(p) for p in port_no(l)), f"{l['in_floor']:.0f}'", f"{l['leader'] / 2:.0f}'", f"{l['total']:.0f}'",
                           f"{l['q']:,.0f}", f"{l['gpm']:.2f} gpm", f"{l['head']:.1f} ft", f"{l['t_surf']:.0f}°F"]) for l in loops]
    for z, Z in ZONES.items():
        lz = [l for l in loops if l['zone'] == z]
        loop_rows.append((Z['stat'], [f"Zone {z[1:]}", z[1:], Z['name'], ', '.join(sorted({l['st'] for l in lz})), '', f"{len(lz)} loops", '', f"{sum(l['total'] for l in lz):,.0f}'",
                                       f"{sum(l['q'] for l in lz):,.0f}", f"{sum(l['gpm'] for l in lz):.1f} gpm", '', '']))
    mf_rows = []
    for k, st in STATIONS.items():
        on = by_st[k]; fk = 'MF-2' if k == 'MF-G' else k; f = next(f for f in feeds if f['mf'] == fk)
        mf_rows.append((k, [k, f"{len(on)} loops: " + ', '.join(l['id'] for l in on), f"{2 * len(on)} of {len(grid.ports[k])}", st['where'], ', '.join(sorted({l['zone'][1:] for l in on})),
                            f"1\" pair {f['id']}, {f['lf']:.0f}' each way" + (' (shared with MF-2)' if k == 'MF-G' else '')]))
    tables = [
        dict(key='loops', title='Loop schedule', lede='Ports are the supply and return positions counted from the low end of the manifold\'s row. Leader is each way. Heat includes the share lost downward. Pick a row to find the loop.',
             cols=['Loop', 'Zone', 'Rooms', 'Manifold', 'Ports', 'In field', 'Leader', 'Total', 'Btu/h', 'Flow', 'Head', 'Floor'], rows=loop_rows),
        dict(key='manifolds', title='Manifolds', lede='Each station\'s row of 3" port positions along its wall; a loop takes two next to each other.', cols=['Tag', 'Loops', 'Ports used', 'Where', 'Zones', 'Feed'], rows=mf_rows),
        dict(key='bom', title='Bill of materials', lede='Rough-order quantities from the drawing geometry, for pricing. The installer takes off the final list.', cols=['Item', 'Qty', 'Notes'], rows=[
            (None, ['1/2" O2-barrier PEX, 1,000\' coils', f'{n_coils} coils', f"{tot_tube:,.0f}' in {len(loops)} uncut lengths of {shortest['total']:.0f}' to {longest['total']:.0f}' (the schedule), cut longest first"]),
            (None, [BOARD['name'] + f", {BOARD['size']:.0f}' x {BOARD['size']:.0f}'", f'{boards} boards ({bundles} bundles of {BOARD["per_bundle"]})', f"{slab_sf:,} sq ft of slab + 5% for cuts; R-{BOARD['r']:.0f}, 1/2\" tube channels on 3\" centres"]),
            (None, ['1" PEX supply + return, insulated', f"{feed_lf * 2 * 1.05:.0f} lf", 'HS-1 to the stations, in the base course under the boards']),
            (None, ['Stainless manifolds with flow meters', f"{len(STATIONS)} stations", ', '.join(f"{k} {len(by_st[k])}-loop" for k in STATIONS) + ' (MF-G as two manifolds side by side)']),
            (None, ['24 V thermal actuators', str(len(loops)), 'one per loop, on the return port']),
            (None, ['Zone controller + thermostats', '1 + 4', 'T1, T2, T3, TG; outdoor reset sensor']),
            (None, ['Circulators', '2', 'P-R1 constant ΔP for the house, P-RG for the garage with its mixing valve']),
            (None, ['Manifold cabinets', str(len(STATIONS)), 'recessed at MF-K, MF-5, MF-3 and MF-4; surface at MF-1, MF-2 and MF-G']),
            (None, ['R-10 rigid foam, 2", slab edge', f"{round(plen(plumbing.OUTLINE + plumbing.OUTLINE[:1]) * 1.05):,} lf", 'the perimeter of the slab, full depth']),
            (None, ['10-mil vapor barrier', f"{slab_sf * 1.1:,.0f} sf", 'under the boards, lapped and taped']),
            (None, ['Pipe insulation, 1/2" x 12"', f"{2 * len(loops)} pcs", 'one sleeve on every tube end where it rises out of the concrete']),
        ]),
    ]
    summary = dict(loops=len(loops), tube_ft=round(tot_tube), heat=round(tot_q), house_heat=round(house_q), gpm=round(tot_gpm, 1), supply_f=t_supply, manifolds=len(STATIONS), boards=boards)
    # 3D model (build/app_template.html, the radiant section): one tube mesh per loop on the boards, the manifold cabinets with their
    # riser bundles, the 1" feed pairs under the boards, HS-1, the thermostats and the board layer as a ghost. Heights are feet from the slab top.
    loops3d = []
    for l in loops:
        loops3d.append(dict(id=l['id'], zone=l['zone'], color=ZONES[l['zone']]['color'], mf=l['st'], rise=list(station_at(STATIONS[l['st']])),
                            name=f"{l['id']} · zone {l['zone'][1:]}, {', '.join(l['room_names'])}",
                            text=f"{l['total']:.0f}' of 1/2\" PEX at 6\" o.c. on the nub boards, {l['gpm']:.2f} gpm, to {l['st']} ports {'/'.join(str(p) for p in port_no(l))} (R-1)",
                            paths=[[list(p) for p in corners_ft(l['tube'])]], panels=[list(r) for r in l['rects']]))
    stations3d = []
    for k, st in STATIONS.items():
        on = by_st[k]; lo, hi = st['mount']
        stations3d.append(dict(id=k, at=list(station_at(st)), box=list(station_box(st, grow=0.2, depth=0.35)), z=[lo, hi], name=f"{k} · radiant manifold, {len(on)} loops",
                               text=f"{st['detail']} Loops {', '.join(l['id'] for l in on)}; {sum(l['gpm'] for l in on):.1f} gpm with all calling (R-1)."))
    feeds3d = [dict(id=f['id'], mf=f['mf'], pts=[list(p) for p in f['pts']], name=f"{f['id']} · 1\" feed pair to {f['to']}",
                    text=f"1\" PEX supply and return from HS-1, about {f['lf']:.0f}' each way, insulated, in the base course under the boards (R-1)") for f in feeds]
    hs3d = dict(id='HS-1', box=[33.0, 48.0, 33.9, 49.6], z=[2.5, 5.0], name='HS-1 · condensing boiler',
                text="Gas or propane condensing boiler for the slab, wall-hung on the mechanical closet's east wall, with P-R1, P-RG, the mixing valves and the zone controller; circuit 27 (R-1)")
    stats3d = [dict(id=Z['stat'], at=list(STATS[Z['stat']]), color=Z['color'], name=f"{Z['stat']} · zone {z[1:]} thermostat", text=f"{Z['name']}: {Z['where']} (R-1)") for z, Z in ZONES.items()]
    foam3d = dict(z=[BOARD_Z[0], BOARD_Z[0] + BOARD['eps_in'] / 12], name=f"Boards · {BOARD['name']}, R-{BOARD['r']:.0f}", ref='Board',
                  text=f"{BOARD['thick_in']:.0f}\" nub boards under the whole slab: {BOARD['eps_in']:.0f}\" of EPS under a {BOARD['puck_in']:.0f}\" grid of pucks on {BOARD['pitch_in']:.0f}\" centres that hold the tube; 4\" of concrete over the pucks (R-1)")
    r3d = dict(slab_h=SLAB_H, feed_h=FEED_H, loops=loops3d, stations=stations3d, feeds=feeds3d, hs=hs3d, stats=stats3d, foam=foam3d)
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, legend=legend, r3d=r3d, loops=loops)
