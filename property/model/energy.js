// Hour-by-hour heating and cooling for 64 Stone Sheep Circle on a typical Casper
// year (TMY3). One thermal node: the house's envelope conductance (UA), air leakage
// and ventilation, sun through the windows, internal gains and the thermal mass of
// the slab and framing. The thermostat holds the heating and cooling setpoints and
// the model records what the equipment had to supply each hour.
//
// Inputs come from data/house-data.json (areas measured from the plans) and the
// settings on the page. Nothing here knows about the DOM.

export const DEFAULTS = {
  front: 180,            // azimuth the front porch faces (deg from north); the plans give a north arrow but no lot
  wallR: 22, ceilingR: 49, vaultR: 38, windowU: 0.28, shgc: 0.40, doorU: 0.20,
  slabF: 0.54,           // slab-edge F-factor, BTU/h·ft·°F (R-10 edge insulation)
  ach50: 3.0, nFactor: 16, // blower-door target and the LBL divisor for a one-story house
  ventCfm: 0,            // 0 = ASHRAE 62.2 rate for the house
  ervEff: 0.70,          // ERV sensible recovery; 0 = exhaust-only ventilation
  heatSet: 70, coolSet: 75,
  massPerSf: 6,          // BTU/°F per sq ft of floor (slab, drywall, framing, furniture)
  system: 'hp',          // hp | propane | gas
  tons: 3.5, backupKw: 5, seer2: 17, afue: 0.95,
  elec: 0.13, propane: 2.60, gas: 1.05, // $/kWh, $/gal, $/therm
};

const BTU_PER_KWH = 3412.14, BTU_PER_GAL_PROPANE = 91500, BTU_PER_THERM = 100000;
const WH_M2_TO_BTU_FT2 = 0.3170;

// Cold-climate heat pump: delivered capacity as a fraction of nominal, and COP, by outdoor °F.
const HP_CAP = [[-22, 0.62], [-10, 0.85], [5, 0.95], [17, 1.0], [47, 1.0]];
const HP_COP = [[-22, 1.35], [-10, 1.7], [5, 2.1], [17, 2.6], [30, 3.1], [47, 3.8], [62, 4.4]];
const AC_COP = [[70, 1.30], [82, 1.0], [95, 0.78], [105, 0.68]]; // multiplier on SEER2/3.412

const lerp = (tbl, x) => {
  if (x <= tbl[0][0]) return tbl[0][1];
  for (let i = 1; i < tbl.length; i++) if (x <= tbl[i][0]) {
    const [x0, y0] = tbl[i - 1], [x1, y1] = tbl[i];
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
  }
  return tbl[tbl.length - 1][1];
};
const rad = d => d * Math.PI / 180;

// The four sides of the plan: front is +Y on the sheets, left is the garage-door wall (X = 0).
export function sideAzimuths(front) {
  const n = a => ((a % 360) + 360) % 360;
  return { front: n(front), rear: n(front + 180), left: n(front + 90), right: n(front - 90) };
}

// Conductances in BTU/h·°F, split out so the page can show where the heat goes.
export function conductances(house, p) {
  const e = house.envelope, t = house.totals, beds = house.rooms.filter(r => r.kind === 'bed').length;
  const alt = house.climate.altitude_factor;
  const cfa = t.conditioned_room_sf;
  const vent = p.ventCfm > 0 ? p.ventCfm : 0.03 * cfa + 7.5 * (beds + 1);
  const achNat = p.ach50 / p.nFactor;
  const ua = {
    walls: e.walls / p.wallR,
    windows: e.windows * p.windowU,
    doors: e.doors * p.doorU,
    ceiling: e.ceiling / p.ceilingR,
    vault: e.vault / p.vaultR,
    slab: e.slab_ft * p.slabF,
    garage: 0.5 * e.garage_wall / p.wallR, // the garage runs about halfway between inside and outside
    leakage: 1.08 * alt * achNat * e.volume / 60,
    ventilation: 1.08 * alt * vent * (1 - p.ervEff),
  };
  return { ua, total: Object.values(ua).reduce((a, b) => a + b, 0), ventCfm: vent, achNat };
}

// Sun on a vertical window, Wh/m², for hour i of the TMY year (hour-ending, local standard time).
function sunFactory(wx) {
  const lat = rad(wx.lat), lon = wx.lon, merid = wx.tz * 15;
  return (i, azSurf) => {
    const doy = Math.floor(i / 24) + 1, hr = (i % 24) + 0.5;
    const B = rad(360 * (doy - 81) / 364);
    const eot = 9.87 * Math.sin(2 * B) - 7.53 * Math.cos(B) - 1.5 * Math.sin(B); // minutes
    const solar = hr + (4 * (lon - merid) + eot) / 60;
    const w = rad(15 * (solar - 12));
    const dec = rad(23.45 * Math.sin(rad(360 * (284 + doy) / 365)));
    const sinAlt = Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(w);
    const H = wx.hourly, dni = H.dni[i], dhi = H.dhi[i], ghi = H.ghi[i];
    const diffuse = dhi * 0.5 + ghi * 0.2 * 0.5; // sky half plus ground reflection (albedo 0.2)
    if (sinAlt <= 0) return { beam: 0, diffuse };
    const alt = Math.asin(sinAlt);
    let cosAz = (Math.sin(dec) - sinAlt * Math.sin(lat)) / (Math.cos(alt) * Math.cos(lat));
    cosAz = Math.max(-1, Math.min(1, cosAz));
    let az = Math.acos(cosAz) * 180 / Math.PI; if (w > 0) az = 360 - az;
    const cosT = Math.cos(alt) * Math.cos(rad(az - azSurf));
    return { beam: dni * Math.max(0, cosT), diffuse };
  };
}

export function simulate(house, wx, params = {}) {
  const p = { ...DEFAULTS, ...params };
  const { ua, total: UA, ventCfm, achNat } = conductances(house, p);
  const uaNoSlab = UA - ua.slab;
  const t = house.totals, beds = house.rooms.filter(r => r.kind === 'bed').length;
  const C = p.massPerSf * t.conditioned_room_sf;
  const internal = (17900 + 4104 * beds + 4.2 * t.conditioned_room_sf) / 24; // RESNET daily gains, BTU/h
  const az = sideAzimuths(p.front), sun = sunFactory(wx);
  const glass = house.glazing.map(g => ({ ...g, az: az[g.side] }));
  // the patio French doors are glass too
  glass.push({ id: 'D2', side: 'rear', sf: 6 * 6.67 * 0.7, shaded: true, az: az.rear });

  const N = wx.hourly.t.length, nomCap = p.tons * 12000, backupCap = p.backupKw * BTU_PER_KWH;
  const acCop = p.seer2 / 3.412;
  const month = Array.from({ length: 12 }, () => ({ heat: 0, cool: 0, kwh: 0, coolKwh: 0, fuel: 0, backupKwh: 0, solar: 0 }));
  const hourly = { tout: new Float32Array(N), tin: new Float32Array(N), heat: new Float32Array(N), cool: new Float32Array(N), backup: new Float32Array(N), solar: new Float32Array(N) };
  const MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const monthOf = []; MDAYS.forEach((d, m) => { for (let k = 0; k < d * 24; k++) monthOf.push(m); });

  let tin = p.heatSet, peakHeat = 0, peakCool = 0, unmet = 0, backupHours = 0, hpKwh = 0, backupKwh = 0, coolKwh = 0, fuelBtu = 0, blowerKwh = 0;
  for (let i = 0; i < N; i++) {
    const tout = wx.hourly.t[i] * 9 / 5 + 32;
    let solar = 0;
    for (const g of glass) {
      const s = sun(i, g.az);
      solar += g.sf * p.shgc * 0.85 * (g.shaded ? s.diffuse * 0.6 : s.beam + s.diffuse) * WH_M2_TO_BTU_FT2;
    }
    const loss = uaNoSlab * (tin - tout) + (tout < tin ? ua.slab * (tin - tout) : 0);
    let tfree = tin + (internal + solar - loss) / C;
    let heat = 0, cool = 0;
    if (tfree < p.heatSet) { heat = (p.heatSet - tfree) * C; tin = p.heatSet; }
    else if (tfree > p.coolSet) { cool = (tfree - p.coolSet) * C; tin = p.coolSet; }
    else tin = tfree;
    const m = monthOf[i];
    if (heat > 0) {
      if (p.system === 'hp') {
        const cap = nomCap * lerp(HP_CAP, tout), hp = Math.min(heat, cap), extra = heat - hp;
        const k1 = hp / lerp(HP_COP, tout) / BTU_PER_KWH, k2 = Math.min(extra, backupCap) / BTU_PER_KWH;
        if (extra > backupCap + 1) unmet++;
        if (extra > 1) backupHours++;
        hpKwh += k1; backupKwh += k2; month[m].kwh += k1 + k2; month[m].backupKwh += k2; hourly.backup[i] = extra;
      } else {
        const f = heat / p.afue, b = heat / 1000 * 0.009; // furnace blower, kWh per 1000 BTU delivered
        fuelBtu += f; blowerKwh += b; month[m].fuel += f; month[m].kwh += b;
      }
    }
    if (cool > 0) {
      const k = cool / (acCop * lerp(AC_COP, tout)) / BTU_PER_KWH;
      coolKwh += k; month[m].kwh += k; month[m].coolKwh += k;
    }
    month[m].heat += heat; month[m].cool += cool; month[m].solar += solar;
    peakHeat = Math.max(peakHeat, heat); peakCool = Math.max(peakCool, cool);
    hourly.tout[i] = tout; hourly.tin[i] = tin; hourly.heat[i] = heat; hourly.cool[i] = cool; hourly.solar[i] = solar;
  }

  const heatBtu = month.reduce((a, m) => a + m.heat, 0), coolBtu = month.reduce((a, m) => a + m.cool, 0);
  const elecKwh = hpKwh + backupKwh + coolKwh + blowerKwh;
  const fuelUnits = p.system === 'propane' ? fuelBtu / BTU_PER_GAL_PROPANE : p.system === 'gas' ? fuelBtu / BTU_PER_THERM : 0;
  const fuelCost = fuelUnits * (p.system === 'propane' ? p.propane : p.system === 'gas' ? p.gas : 0);
  const heatCost = (hpKwh + backupKwh + blowerKwh) * p.elec + fuelCost, coolCost = coolKwh * p.elec;
  const fuelPrice = p.system === 'propane' ? p.propane / BTU_PER_GAL_PROPANE : p.system === 'gas' ? p.gas / BTU_PER_THERM : 0;
  month.forEach(m => { m.coolCost = m.coolKwh * p.elec; m.heatCost = (m.kwh - m.coolKwh) * p.elec + m.fuel * fuelPrice; m.cost = m.heatCost + m.coolCost; });
  const designF = house.climate.heat_design_f;
  return {
    params: p, ua, UA, ventCfm, achNat, C, internal,
    heatMMBtu: heatBtu / 1e6, coolMMBtu: coolBtu / 1e6,
    peakHeat, peakCool, designLoss: UA * (p.heatSet - designF), designF,
    hpKwh, backupKwh, coolKwh, blowerKwh, elecKwh, fuelUnits, heatCost, coolCost, total: heatCost + coolCost,
    backupHours, unmet, month, hourly,
    hpCapAtDesign: nomCap * lerp(HP_CAP, designF),
  };
}

// Same weather and house, every heating system, for the comparison table.
export function compareSystems(house, wx, params) {
  return ['hp', 'propane', 'gas'].map(system => ({ system, r: simulate(house, wx, { ...params, system }) }));
}
