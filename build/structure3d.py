"""The 3D model's structure layers, built from the S-1 wall runs and the roof truss layout:

  framing  plates, studs, kings, jacks, headers, sills and cripples for every wall run (S-1), stud by stud
  truss    the roof trusses, girder, rafters and beams (build/roof.py)
  grid     the 5' x 5' layout grid from the 0,0 datum

Boxes are [x0, y0, x1, y1, bottom, top, material] in plan feet (heights above the slab); one list per wall run
so the page can merge each run into a mesh and pick it as a whole.
"""
from setlib import HOUSE, ft_in
import framing

CEIL = HOUSE['meta']['ceiling_ft']
STUD = 1.5 / 12
PLATE = 1.5 / 12
TOP_PLATE = CEIL + 1.125 / 12 + 0.0   # 9'-1 1/8" to the top of the double top plate
MATS = ['wood', 'sound', 'header', 'pt', 'block', 'wood6']   # Zero Rd framing colours: 2x4, staggered, header, PT plate, blocking, 2x6


def frame_run(r):
    """Every member of one wall run, Zero Rd style: PT bottom plate, double top plate, studs at 16" (staggered
    walls: 2x4 at 12" on alternating faces of 2x6 plates), kings, jacks, headers, sills and cripples."""
    out = []
    c0, c1 = r['c0'], r['c1']
    depth = c1 - c0
    staggered = r['kind'] == 'S'
    stud_d = 3.5 / 12 if staggered else depth
    mat = 1 if staggered else 5 if r['kind'] == 'E' else 0
    top = TOP_PLATE

    def place(a0, a1, b, t, m=mat, face=0, d=None):
        d = depth if d is None else d
        k0, k1 = (c0, c1) if face == 0 else (c0, c0 + d) if face < 0 else (c1 - d, c1)
        if a1 - a0 < 1e-3 or t - b < 1e-3: return
        box = [a0, k0, a1, k1, b, t, m] if r['horiz'] else [k0, a0, k1, a1, b, t, m]
        out.append([round(v, 3) if isinstance(v, float) else v for v in box])

    a0, a1 = r['a0'], r['a1']
    place(a0, a1, 0, PLATE, 3)                              # PT bottom plate
    place(a0, a1, top - 2 * PLATE, top, mat)                # double top plate
    ext = r['kind'] == 'E'
    ops = []
    for o in r['openings']:
        mid = (o['span'][0] + o['span'][1]) / 2
        w = framing.ro_width(o)
        lo, hi = max(a0, mid - w / 2), min(a1, mid + w / 2)
        if o.get('kind') == 'pocket':   # the pocket runs to the side of the leaf opening away from the wall end it is nearer
            lo, hi = (o['span'][0], o['span'][0] + w) if o['span'][0] - a0 < a1 - o['span'][1] else (o['span'][1] - w, o['span'][1])
            lo, hi = max(a0, lo), min(a1, hi)
        _, hd, jacks = framing.header(o, ext)
        head = min(framing.ro_head(o), top - 2 * PLATE - hd)
        sill = (o['sill'] - 0.25 / 12) if o['otype'] == 'window' else 0
        ops.append((lo, hi, head, sill, hd, jacks, o))
    stud_b, stud_t = PLATE, top - 2 * PLATE
    blocked = lambda p: any(lo - STUD * (j + 1) - 0.01 < p < hi + STUD * (j + 1) + 0.01 for lo, hi, _, _, _, j, _ in ops)
    oc = 1.0 if staggered else 16 / 12
    n, p = 0, a0 + STUD / 2
    while p < a1 - STUD / 2:
        if not blocked(p):
            face = (1 if n % 2 else -1) if staggered else 0
            place(p - STUD / 2, p + STUD / 2, stud_b, stud_t, mat, face, stud_d if staggered else None)
        n += 1; p += oc
    place(a1 - STUD, a1, stud_b, stud_t)                    # end stud, full depth
    for lo, hi, head, sill, hd, jacks, o in ops:
        for k in range(jacks):
            place(lo - STUD * (k + 1), lo - STUD * k, stud_b, head)          # jacks
            place(hi + STUD * k, hi + STUD * (k + 1), stud_b, head)
        place(lo - STUD * (jacks + 1), lo - STUD * jacks, stud_b, stud_t)    # kings
        place(hi + STUD * jacks, hi + STUD * (jacks + 1), stud_b, stud_t)
        hl, hh = lo - STUD * jacks, hi + STUD * jacks
        place(hl, hh, head, head + hd, 2)                                    # header: built-up 7-1/4" outside, a flat 2x4 inside
        p = lo + 16 / 12
        while p < hi - 0.05:                                                  # cripples above, and below a window
            place(p - STUD / 2, p + STUD / 2, head + hd, stud_t)
            if sill > 0.3: place(p - STUD / 2, p + STUD / 2, stud_b, sill - 2 * PLATE)
            p += 16 / 12
        if sill > 0.3: place(lo, hi, sill - 2 * PLATE, sill, mat)           # double sill
    return out


def build(s1):
    R, T, BL = s1['runs'], s1['roof'], s1['blocking']
    runs = []
    for r in R:
        ops = ', '.join(f"{o['id']} RO {framing.rough(o)}, {framing.header(o, r['kind'] == 'E')[0]}" for o in r['openings'])
        oc = 'studs 12" o.c. on alternating faces' if r['kind'] == 'S' else 'studs 16" o.c.'
        text = (f"Framing, wall {r['n']}: {r['type']}, {ft_in(r['len'])}; PT bottom plate, {oc}, double top plate at 9'-1 1/8\". "
                + (f"Openings: {ops}. " if ops else '') + 'See S-1.')
        runs.append(dict(name=f"Wall {r['n']} · {r['type']}", ref=f"Wall {r['n']}", text=text, boxes=frame_run(r)))
    # blocking bands as thin boxes on the stud face, at a typical height for the item
    for b in BL:
        x0, y0, x1, y1 = b['band']
        bands = {'Grab bars and paper holder': [(2.62, 3.0)], 'Grab bars, valve and bench': [(2.62, 3.0), (3.88, 4.25)], 'Grab bars and valve': [(2.62, 3.0)],
                 'Cabinets and vanity top': [(2.75, 2.96), (6.88, 7.08)], 'Washer box': [(3.0, 4.0)], 'TV above the fireplace': [(4.0, 6.0)]}[b['what']]
        e = 0.06
        boxes = [[x0, y0 - e, x1, y1 + e, h0, h1, 4] if y0 == y1 else [x0 - e, y0, x1 + e, y1, h0, h1, 4] for h0, h1 in bands]
        runs.append(dict(name=f"Blocking · wall {b['wall']}", ref=f"Wall {b['wall']}", text=f"Blocking on wall {b['wall']}, {b['what'].lower()} for the {b['name'].lower()}: {b['how']}. See the S-1 blocking schedule.",
                         boxes=[[round(v, 3) if isinstance(v, float) else v for v in bx] for bx in boxes]))
    trusses = [dict(axis=t['axis'], s=t['s'], m=t['members'], k=t['kind'], ref=t['mark'], name=f"Roof truss {t['mark']}" if t['kind'] not in ('rafter',) else ('Patio rafter' if t['area'] == 'PR' else 'Porch rafter'), text=t['text'])
               for t in T['trusses']]
    grid = dict(x=list(range(0, 90, 5)), y=list(range(0, 75, 5)), extent=[-2.0, -2.0, 87.0, 72.0],
                note="0,0 datum: the outside face of the garage-door wall (X) and the line of the master bedroom's rear wall (Y). Grid 5'-0\" each way; X to the right, Y toward the porch. Same grid as every sheet.")
    return dict(mats=MATS, runs=runs, trusses=trusses, beams=T['beams'], grid=grid)
