// The Cloudflare Worker for 64 Stone Sheep Circle. Static files come straight
// from the assets. The property app (/property/*) and its sync store (/api/*)
// are private: Cloudflare Access must sit in front of them, and the Worker
// checks Access's signed token itself, so a path left out of Access, or a
// workers.dev preview, still can't show the budget. The contractor app stays
// public for the crews.
import { DurableObject } from 'cloudflare:workers';

// One Durable Object holds every synced document, keyed by its name ("budget").
export class Store extends DurableObject {
  async read(key) { return (await this.ctx.storage.get(key)) ?? null; }
  async write(key, data) { await this.ctx.storage.put(key, data); }
}

const PRIVATE = /^\/(property|api)(\/|$)/;
const KEY = /^[a-z0-9-]{1,40}$/;
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const text = (body, status) => new Response(body, { status, headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store' } });

// Access puts a signed token (RS256) on every request it lets through. It must be
// signed by this team's current keys, issued for this application, and unexpired.
let keys = null, keysAt = 0;
const b64u = s => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(s.length / 4) * 4, '=')), c => c.charCodeAt(0));
const part = s => JSON.parse(new TextDecoder().decode(b64u(s)));
export async function verifyAccess(token, team, aud, fetchKeys = url => fetch(url).then(r => r.json())) {
  if (!token) return false;
  try {
    const [h, p, sig] = token.split('.'), head = part(h), claims = part(p);
    const iss = `https://${team}.cloudflareaccess.com`;
    const auds = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
    if (head.alg !== 'RS256' || claims.iss !== iss || !auds.includes(aud) || !(claims.exp > Date.now() / 1000)) return false;
    if (!keys || Date.now() - keysAt > 3600e3 || !keys.some(k => k.kid === head.kid)) { keys = (await fetchKeys(`${iss}/cdn-cgi/access/certs`)).keys; keysAt = Date.now(); }
    const jwk = keys.find(k => k.kid === head.kid);
    if (!jwk) return false;
    const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
    return await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64u(sig), new TextEncoder().encode(`${h}.${p}`));
  } catch { return false; }
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === '/property' || url.pathname === '/property/') return Response.redirect(new URL('/property/home.html', url), 302);
    // a folder address serves its index.html (html_handling is off)
    const asset = () => env.ASSETS.fetch(url.pathname.endsWith('/') ? new Request(new URL(url.pathname + 'index.html' + url.search, url), req) : req);
    if (!PRIVATE.test(url.pathname)) return asset();

    if (!env.ACCESS_TEAM || !env.ACCESS_AUD) return text('The property app is private. Finish the Cloudflare Access setup (README, "Hosting on Cloudflare") to open it.', 503);
    if (!(await verifyAccess(req.headers.get('cf-access-jwt-assertion'), env.ACCESS_TEAM, env.ACCESS_AUD))) return text('Sign-in required.', 403);
    if (!url.pathname.startsWith('/api/')) return asset();

    // /api/ping, and /api/doc/<key> to GET or PUT one JSON document
    const [kind, key, ...rest] = url.pathname.slice(5).split('/').filter(Boolean);
    if (kind === 'ping') return json({ ok: true });
    if (kind !== 'doc' || !key || rest.length || !KEY.test(key)) return json({ error: 'not found' }, 404);
    const store = env.STORE.get(env.STORE.idFromName('main'));
    if (req.method === 'GET') { const data = await store.read(key); return json({ exists: data != null, data }); }
    if (req.method === 'PUT') {
      const body = await req.text();
      if (body.length > 1_000_000) return json({ error: 'too big' }, 413);
      let data; try { data = JSON.parse(body); } catch { return json({ error: 'bad json' }, 400); }
      if (!data || typeof data !== 'object' || Array.isArray(data)) return json({ error: 'bad json' }, 400);
      await store.write(key, data);
      return json({ ok: true });
    }
    return json({ error: 'method' }, 405);
  },
};
