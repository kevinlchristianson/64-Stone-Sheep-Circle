# 64 Stone Sheep Circle: plan breakdown

Source: `plan/source/larson-house-plans-2026-06-11.pdf`, six 36" × 24" sheets titled "Larson House", dated 6/11/26, scale 1/4" = 1'-0". Wall geometry below comes straight out of the A-1 vector drawing; the numbers were checked against the sheet's dimension strings.

## The sheets

| Sheet | What it shows |
|---|---|
| A-1 | First floor plan: walls, doors, windows, room names with sizes and areas, full dimension strings |
| A-2 | Roof plan laid over the floor plan: hips and gables, pitches (6:12, 8:12, 2:12), the vaulted areas |
| A-3 (site) | Lot outline with the house, a north arrow, no dimensions |
| A-3 (elevations) | Front and rear views (two sheets carry the number A-3) |
| A-4 | Left and right views |
| A-5 | The A-1 plan with fixtures, cabinets and appliances and their tags |

## The house in one paragraph

A one-story ranch, 83'-5¼" across the front and 70'-1" deep at the garage, about **3,185 sq ft heated** (to outside faces) plus a **~980 sq ft two-car garage**, a **~400 sq ft covered front porch** and a **~325 sq ft covered rear patio**. Three wings: the master suite and garage on the left, the open kitchen/dining/living in the middle, three bedrooms and two baths down a hall on the right. Walls are drawn 5½" exterior (2x6) and 3½" interior (2x4). Ceilings are 9' everywhere except a **4:12 vault over the kitchen and living room** and a **6:12 vaulted patio ceiling**. Roof is standing-seam metal over hips and gables (6:12 main, 8:12 gables, 2:12 porch). Siding is vertical board-and-batten with a stone-veneer front gable on the garage and timber posts and a gable bracket at the entry.

## Rooms

Sizes and areas as printed on A-1; "measured" is the interior-face area from the wall data.

| Room | A-1 size | A-1 sf | Measured sf | Notes |
|---|---|---|---|---|
| Master Bed | 14' × 17' | 258 | 241 | Bumps out 5'-1" past the rear wall; two rear windows |
| Master Bath | 10'-3" × 18'-7" | 189 | 193 | Pedestal tub, 8' double vanity, ADA toilet, 4' × 6' glass shower, 4'-6" high window |
| Master Closet | 10'-2" × 9'-4" | 107 | 96 | Pocket door through to the laundry |
| Laundry | 8'-4" × 12'-1" | 100 | 101 | Curved-front washer and dryer, cabinets |
| Powder | 5'-5" × 5'-5" | 34 | 30 | Toilet only drawn on A-5 (no sink shown) |
| Mud Room | 14'-1" × 6'-6" | 145 | 133 | L-shaped, runs down to the garage door |
| Kitchen | 13' × 28'-9" | 376 | 371 | 48" range on the left wall, 4'-5" × 11'-11" island, 35" fridge, vaulted |
| Dining | 12'-10" × 10'-7" | 147 | 136 | Three rear windows and two onto the patio |
| Pantry | 9'-5" × 8' | 81 | 77 | Front window |
| Mechanical | 3' × 8' | 30 | 25 | Opens to the garage through double doors; floor drain |
| Living | 17'-4" × 25'-7" | 512 | 525 | Vaulted; wood fireplace insert on the hall wall; 6' French doors to the patio |
| Entry | 7' × 10'-7" | 80 | 76 | Coat closet; open to the living room |
| Office | 12'-9" × 10'-5" | 143 | 134 | French doors off the entry, front window |
| Bedroom 1 | 13'-1" × 13'-4" | 189 | 176 | Own bath (Bath 1), 6' reach-in closet |
| Bath 1 | 5' × 6'-11" | 42 | 53 | Toilet, sink, 5' × 3'-4" shower |
| Bedroom 2 | 14'-1" × 12'-6" | 190 | 178 | 5' × 5' closet, two side windows |
| Bath 2 | 14'-1" × 5'-6" | 87 | 79 | 8' double vanity, toilet, 66" tub |
| Bedroom 3 | 12'-11" × 12'-11" | 181 | 169 | 5'-2" × 4'-11" closet, one front window |
| Garage | 30' × 32'-11" | 978 | 942 | Two 9' overhead doors on the left side, three front windows, service door at the rear, floor drain |

## Openings

- **20 windows.** Sixteen 2'-6" units (bedrooms, dining, living, master bed, garage), three 4'-0" units on the porch wall (pantry, office, bedroom 3) and one 4'-6" high window in the master bath. Heights are not dimensioned; scaled from the elevations they read as 2'-6" × 5'-0" and 4' × 4' with heads at 8'-0".
- **Exterior doors:** front entry 3'-0", 6' French doors to the patio, a 3'-0" garage service door, two 9' overhead garage doors.
- **Interior:** 16 doors (swing, pocket, bypass, French, the garage fire door and the mechanical double doors) plus six cased openings. Interior door heights aren't on the plans.

## Systems the plans call out (A-5)

- Plumbing fixtures: 4 ADA toilets, 5 lavatories (plus the powder sink the plan doesn't show), 1 pedestal tub, 1 standard 66" tub, 2 showers, kitchen sink and dishwasher on the island, washer, floor drains in the garage and mechanical closet (Kohler drain tags K-9135 and K-9136).
- Appliances: 48" range (tagged BS655Z-48 / GEM-FPF), 35" refrigerator, curved-front washer and dryer.
- Hearth: a wood-burning fireplace insert in the living room.
- No electrical, mechanical, plumbing-riser, framing, foundation or structural sheets are in the set.

## Gaps and things to settle

1. **Location and climate.** Neither the plans nor a quick search say where 64 Stone Sheep Circle is. The energy model and HVAC sizing default to the Casper, WY weather file already in the 7824 Zero Rd apps until this is confirmed.
2. **Living room label.** A-1 prints 17'-4" × 25'-7" but the walls put it at about 20'-5" × 25'-7"; the printed 512 sq ft matches the wider figure.
3. **Bedroom egress.** Bedroom 3 has one 4' × 4' window whose sill scales at about 4'-0", above the 44" egress limit; every bedroom window needs a confirmed 5.7 sq ft net opening.
4. **Garage separation.** The door from the garage to the mud room and the mechanical closet's double doors open off the garage; they need the fire-rated, self-closing treatment the code asks for, and the mechanical closet's combustion air depends on what goes in it.
5. **Powder room sink** isn't drawn.
6. **Fireplace** needs a chimney or flue route through the vaulted living ceiling; none is shown.
7. **Site plan** has no dimensions, setbacks, driveway, well/septic or utility locations.
8. **Duplicate sheet number:** the site plan and the front/rear elevations are both labeled A-3.
9. No window/door schedule, header sizes, foundation type, insulation values or structural design.
