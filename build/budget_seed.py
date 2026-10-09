"""Starting construction budget for the Property App, with quantities taken from the plans.

Unit prices are placeholders for a 2026 Wyoming custom build, meant to be replaced by
bids as they arrive. Writes property/data/budget-seed.json.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def build(house):
    t, tr, env = house['totals'], house['trades'], house['envelope']
    under_roof = t['heated_gross_sf'] + t['garage_gross_sf'] + t['porch_sf'] + t['patio_sf']
    slab = t['heated_gross_sf'] + t['garage_gross_sf'] + t['porch_sf'] + t['patio_sf']
    roof = round(under_roof * 1.12)             # 6:12 / 8:12 slopes plus overhangs
    siding = round(tr['s1']['ext_lf'] * 10.5 - env['windows'] - env['doors'])
    windows = sum(1 for _ in house['glazing'])
    baths = sum(1 for r in house['rooms'] if r['kind'] == 'bath')
    floor = t['conditioned_room_sf']
    L = []
    def add(group, name, qty, unit, price, basis):
        L.append(dict(id=f"b{len(L) + 1}", group=group, name=name, qty=qty, unit=unit, price=price, basis=basis))
    add('Soft costs', 'Permits, plan review and impact fees', 1, 'lot', 9000, 'county fees, placeholder')
    add('Soft costs', 'Engineering (truss, foundation, energy check)', 1, 'lot', 6500, 'the plans have no structural or MEP sheets')
    add('Soft costs', 'Builder\'s risk insurance and temporary utilities', 1, 'lot', 5500, '')
    add('Site', 'Excavation, grading and backfill', 1, 'lot', 28000, 'lot not dimensioned on the plans')
    add('Site', 'Well or water tap, septic or sewer tap', 1, 'lot', 32000, 'depends on the site')
    add('Site', 'Driveway and flatwork', 1, 'lot', 14000, '')
    add('Foundation', 'Footings, stem walls and slab', slab, 'sq ft', 14, f'{slab:,} sq ft under roof (house, garage, porch, patio)')
    add('Foundation', 'Slab-edge and under-slab insulation', env['slab_ft'], 'ft', 18, f"{env['slab_ft']:.0f} ft of heated slab edge")
    add('Framing', 'Wall framing, sheathing and labor', tr['s1']['ext_lf'] + tr['s1']['int_lf'], 'ft of wall', 95, f"{tr['s1']['ext_lf']} ft exterior + {tr['s1']['int_lf']} ft interior (S-1)")
    add('Framing', 'Roof trusses, sheathing and labor', under_roof, 'sq ft', 16, f'{under_roof:,} sq ft under roof')
    add('Roof', 'Standing-seam metal roof', roof, 'sq ft', 12, f'about {roof:,} sq ft of roof surface (A-2 pitches)')
    add('Roof', 'Gutters, downspouts, soffit and fascia', tr['s1']['ext_lf'] + 60, 'ft', 22, 'perimeter plus porch and patio')
    add('Exterior', 'Windows', windows + 3, 'each', 1100, f'{windows} house + 3 garage windows (A-1)')
    add('Exterior', 'Exterior doors (entry, patio French, service)', 3, 'each', 2800, 'D1, D2, D3')
    add('Exterior', 'Garage doors and openers', 2, 'each', 3800, 'two 9\' x 8\' (D4, D5)')
    add('Exterior', 'Board-and-batten siding and trim', siding, 'sq ft', 9, f'about {siding:,} sq ft of wall')
    add('Exterior', 'Stone veneer on the garage gable', 260, 'sq ft', 32, 'A-3 front elevation')
    add('Exterior', 'Porch and patio posts, beams and ceilings', t['porch_sf'] + t['patio_sf'], 'sq ft', 28, '')
    add('Mechanical', 'Heat pump, air handler, ducts and ERV', 1, 'lot', 30000, f"{tr['m1']['tons']}-ton cold-climate heat pump, {tr['m1']['registers']} registers (M-1)")
    add('Mechanical', 'Fireplace and venting', 1, 'lot', 7500, 'living room fireplace, chimney route open')
    add('Plumbing', 'Rough and finish plumbing', tr['p1']['fixtures'], 'fixture', 1900, f"{tr['p1']['fixtures']} fixtures, {tr['p1']['stacks']} stacks (P-1)")
    add('Plumbing', 'Water heater', 1, 'each', 3200, 'heat-pump water heater in the mechanical room')
    add('Electrical', 'Rough and finish wiring', tr['e1']['devices'], 'device', 115, f"{tr['e1']['devices']} devices on {tr['e1']['circuits']} circuits (E-1)")
    add('Electrical', '200 A service, panel and meter', 1, 'lot', 6500, f"load calc about {tr['e1']['amps']} A")
    add('Electrical', 'Light fixtures', tr['e1']['lights'], 'each', 85, '')
    add('Insulation', 'Walls, ceilings and air sealing', round(env['walls'] + env['ceiling'] + env['vault']), 'sq ft', 3.2, 'to the energy page\'s R-values')
    add('Interior', 'Drywall, hang and finish', tr['s1']['wall_board'] + tr['s1']['ceiling_board'], 'sq ft', 3.6, 'wall and ceiling board (S-1)')
    add('Interior', 'Interior doors and trim', 22, 'each', 650, 'A-1 door schedule')
    add('Interior', 'Paint', floor, 'sq ft floor', 4.5, '')
    add('Interior', 'Flooring', floor, 'sq ft', 9, f'{floor:,} sq ft of rooms')
    add('Interior', 'Tile (baths, laundry, mud room)', 650, 'sq ft', 22, f'{baths} baths')
    add('Kitchen & baths', 'Cabinets', 1, 'lot', 38000, 'kitchen, pantry, baths, laundry (A-5)')
    add('Kitchen & baths', 'Countertops', 1, 'lot', 14000, '')
    add('Kitchen & baths', 'Appliances', 1, 'lot', 15000, '')
    add('Kitchen & baths', 'Shower glass, mirrors and accessories', 1, 'lot', 6000, '')
    add('General', 'Builder supervision and overhead', 1, 'lot', 0, 'set this from the builder\'s contract')
    add('General', 'Cleanup, dumpsters and final clean', 1, 'lot', 6000, '')
    return dict(version=1, note='Starting numbers only: quantities come from the plans, prices are placeholders. Replace each line as bids arrive.',
                contingency_pct=10, lines=L)


if __name__ == '__main__':
    house = json.load(open(os.path.join(ROOT, 'property', 'data', 'house-data.json')))
    out = build(house)
    with open(os.path.join(ROOT, 'property', 'data', 'budget-seed.json'), 'w') as f: json.dump(out, f, indent=1)
    total = sum(l['qty'] * l['price'] for l in out['lines'])
    print(f"budget-seed.json: {len(out['lines'])} lines, ${total:,.0f} before contingency, ${total / house['totals']['heated_gross_sf']:,.0f}/sq ft heated")
