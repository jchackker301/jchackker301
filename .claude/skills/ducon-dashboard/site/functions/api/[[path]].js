// Ducon Editor's War Room API. Runs on Cloudflare Pages Functions with a D1 database bound as DB.
// Access control: Cloudflare Access puts the signed-in email in a header. Without it (and not on localhost) every call is refused.

import {SKILL} from '../lib/skill.js';

const TABLES = new Set(['videos', 'events', 'settings', 'skills', 'projects', 'shoots', 'intel']);
const MAX_BODY = 60000;
const MAX_SKILL_BODY = 200000;
const SKILL_NAME = /^[a-z0-9-]{2,60}$/;
const RESERVED_SKILL = 'ducon-dashboard';

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {'content-type': 'application/json', 'cache-control': 'no-store'}
  });
}

async function getAll(db, email) {
  const rows = (await db.prepare('SELECT table_name, id, data FROM records').all()).results;
  const out = {videos: [], events: [], projects: [], shoots: [], intel: [], settings: null};
  for (const r of rows) {
    let d;
    try { d = JSON.parse(r.data); } catch (e) { continue; }
    if (r.table_name === 'settings') {
      if (r.id === 'team') out.settings = d;
    } else if (out[r.table_name]) {
      out[r.table_name].push(Object.assign({}, d, {id: r.id}));
    }
  }
  return out;
}

// Stops a typo from an agent or a script from saving a record the page cannot show.
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;
function badField(table, d, id) {
  const one = (v, ok) => v === undefined || v === null || v === '' || ok(v);
  if (table === 'skills') {
    if (!SKILL_NAME.test(id)) return 'skill name: lowercase letters, numbers and dashes, 2 to 60 characters';
    if (id === RESERVED_SKILL) return 'ducon-dashboard is the built-in skill and cannot be replaced';
    if (typeof d.text !== 'string' || !d.text.trim()) return 'text is required (the SKILL.md content)';
    if (d.description !== undefined && (typeof d.description !== 'string' || d.description.length > 300)) return 'description must be text up to 300 characters';
  }
  const inList = (list) => (v) => list.includes(v);
  const isDate = (v) => typeof v === 'string' && DATE.test(v);
  if (table === 'videos') {
    if (!one(d.tier, inList(['A', 'B', 'C']))) return 'tier must be A, B or C';
    if (!one(d.status, inList(['idea', 'theme', 'ready', 'prod', 'done']))) return 'status must be idea, theme, ready, prod or done';
    if (!one(d.assignee, inList(['Jayson', 'Alex']))) return 'assignee must be Jayson, Alex or empty';
    for (const f of ['postDate', 'editDeadline', 'slotDate', 'deliveredAt', 'readyAt']) {
      if (!one(d[f], isDate)) return f + ' must be YYYY-MM-DD';
    }
    if (typeof d.title !== 'string' || d.title.length > 200) return 'title must be text up to 200 characters';
  }
  if (table === 'events') {
    if (!one(d.eta, (v) => typeof v === 'string' && DATETIME.test(v))) return 'eta must be YYYY-MM-DDTHH:MM';
    if (!one(d.next, isDate)) return 'next must be YYYY-MM-DD';
    if (!one(d.who, inList(['Both', 'Jayson', 'Alex']))) return 'who must be Both, Jayson or Alex';
    if (!one(d.value, inList(['High', 'Medium', 'Low']))) return 'value must be High, Medium or Low';
    if (typeof d.title !== 'string' || d.title.length > 200) return 'title must be text up to 200 characters';
  }
  if (table === 'projects') {
    if (typeof d.title !== 'string' || !d.title.trim() || d.title.length > 200) return 'title is required, up to 200 characters';
    if (!one(d.who, inList(['Both', 'Jayson', 'Alex']))) return 'who must be Both, Jayson or Alex';
    if (!one(d.status, inList(['ongoing', 'paused', 'done']))) return 'status must be ongoing, paused or done';
    if (d.notes !== undefined && (typeof d.notes !== 'string' || d.notes.length > 2000)) return 'notes must be text up to 2000 characters';
    if (d.updates !== undefined) {
      if (!Array.isArray(d.updates) || d.updates.length > 300) return 'updates must be a list (up to 300)';
      for (const u of d.updates) {
        if (!u || typeof u.t !== 'string' || u.t.length > 500 || !isDate(u.d)) return 'each update needs d (YYYY-MM-DD) and t (text up to 500)';
        if (u.k !== undefined && u.k !== '' && u.k !== 'video' && u.k !== 'task') return 'update k must be video or task';
      }
    }
  }
  if (table === 'shoots') {
    if (typeof d.client !== 'string' || !d.client.trim() || d.client.length > 200) return 'client is required, up to 200 characters';
    if (!isDate(d.date)) return 'date must be YYYY-MM-DD';
    if (!one(d.kind, inList(['backyard', 'showroom', 'event']))) return 'kind must be backyard, showroom or event';
    if (!one(d.media, inList(['photo', 'video', 'both']))) return 'media must be photo, video or both';
    if (!one(d.who, inList(['Both', 'Jayson', 'Alex']))) return 'who must be Both, Jayson or Alex';
    if (d.place !== undefined && (typeof d.place !== 'string' || d.place.length > 200)) return 'place must be text up to 200 characters';
    if (d.folder !== undefined && (typeof d.folder !== 'string' || d.folder.length > 500)) return 'folder must be text up to 500 characters';
    if (d.notes !== undefined && (typeof d.notes !== 'string' || d.notes.length > 1000)) return 'notes must be text up to 1000 characters';
    if (d.fromEvent !== undefined && typeof d.fromEvent !== 'string') return 'fromEvent must be an id';
  }
  if (table === 'intel') {
    if (!/^\d{4}-\d{2}$/.test(id)) return 'intel id must be the month, YYYY-MM';
    const text = (v, n) => typeof v === 'string' && v.length <= n;
    const list = (v, n) => Array.isArray(v) && v.length <= n;
    if (d.headline !== undefined && !text(d.headline, 400)) return 'headline must be text up to 400 characters';
    if (d.scannedAt !== undefined && !text(d.scannedAt, 40)) return 'scannedAt must be short text';
    if (d.source !== undefined && !text(d.source, 300)) return 'source must be text up to 300 characters';
    if (d.clues !== undefined) {
      if (!list(d.clues, 60)) return 'clues must be a list (up to 60)';
      for (const c of d.clues) if (!c || !text(c.t, 500)) return 'each clue needs t (text up to 500)';
    }
    if (d.tips !== undefined) {
      if (!list(d.tips, 40)) return 'tips must be a list (up to 40)';
      for (const c of d.tips) if (!c || !text(c.t, 500) || (c.why !== undefined && !text(c.why, 600)) || (c.basis !== undefined && c.basis !== 'chat' && c.basis !== 'inference')) return 'each tip needs t, optional why, basis chat or inference';
    }
    if (d.links !== undefined) {
      if (!list(d.links, 300)) return 'links must be a list (up to 300)';
      for (const c of d.links) if (!c || !isDate(c.d) || !text(c.title, 300) || (c.path !== undefined && !text(c.path, 700)) || (c.kind !== undefined && !['video', 'shoot', 'other'].includes(c.kind)) || (c.who !== undefined && !text(c.who, 40))) return 'each link needs d (YYYY-MM-DD), title, kind video|shoot|other';
    }
    if (d.unconfirmed !== undefined) {
      if (!list(d.unconfirmed, 60)) return 'unconfirmed must be a list (up to 60)';
      for (const c of d.unconfirmed) if (!c || !isDate(c.d) || !text(c.t, 500)) return 'each unconfirmed item needs d (YYYY-MM-DD) and t';
    }
  }
  return '';
}

// Custom skills (added by Jayson or by Claude). Text is only sent to the Skills room, never in /api/all.
async function listSkills(db) {
  const rows = (await db.prepare("SELECT id, data, updated_at FROM records WHERE table_name = 'skills' ORDER BY id").all()).results;
  const out = [];
  for (const r of rows) {
    let d;
    try { d = JSON.parse(r.data); } catch (e) { continue; }
    out.push({name: r.id, description: d.description || '', text: d.text || '', updated: (r.updated_at || '').slice(0, 10)});
  }
  return out;
}

async function put(db, table, id, body, email) {
  if (body.length > (table === 'skills' ? MAX_SKILL_BODY : MAX_BODY)) return json({error: 'Too large'}, 413);
  let data;
  try { data = JSON.parse(body); } catch (e) { return json({error: 'Bad JSON'}, 400); }
  if (data === null || typeof data !== 'object' || Array.isArray(data)) return json({error: 'Object expected'}, 400);
  const bad = badField(table, data, id);
  if (bad) return json({error: 'Not saved: ' + bad}, 400);
  await db.prepare(
    'INSERT INTO records (table_name, id, data, updated_by, updated_at) VALUES (?1, ?2, ?3, ?4, ?5) ' +
    'ON CONFLICT (table_name, id) DO UPDATE SET data = ?3, updated_by = ?4, updated_at = ?5'
  ).bind(table, id, JSON.stringify(data), email, new Date().toISOString()).run();
  return json({ok: true});
}

// Humans: Cloudflare Access signs a JWT (Cf-Access-Jwt-Assertion). We verify signature, issuer, audience and expiry
// against the team's public certs. The plain email header is never trusted. Needs ACCESS_TEAM_DOMAIN and ACCESS_AUD.
let certCache = {at: 0, keys: null};

async function accessKeys(domain) {
  if (certCache.keys && Date.now() - certCache.at < 3600000) return certCache.keys;
  const r = await fetch('https://' + domain + '/cdn-cgi/access/certs');
  const j = await r.json();
  certCache = {at: Date.now(), keys: j.keys || []};
  return certCache.keys;
}

function b64u(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  const bin = atob(s);
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}

async function verifyAccessJwt(token, env) {
  const [h, p, s] = token.split('.');
  if (!h || !p || !s) return '';
  const dec = new TextDecoder();
  const header = JSON.parse(dec.decode(b64u(h)));
  const payload = JSON.parse(dec.decode(b64u(p)));
  if (header.alg !== 'RS256') return '';
  const jwk = (await accessKeys(env.ACCESS_TEAM_DOMAIN)).find(function(k) { return k.kid === header.kid; });
  if (!jwk) return '';
  const key = await crypto.subtle.importKey('jwk', jwk, {name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256'}, false, ['verify']);
  const ok = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64u(s), new TextEncoder().encode(h + '.' + p));
  if (!ok) return '';
  const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (aud.indexOf(env.ACCESS_AUD) < 0) return '';
  if (payload.iss !== 'https://' + env.ACCESS_TEAM_DOMAIN) return '';
  if (!payload.exp || payload.exp * 1000 < Date.now()) return '';
  return String(payload.email || '').toLowerCase();
}

// Agents (Claude and other tools) call /api/agent/... with "Authorization: Bearer <AGENT_API_KEY>".
// The key lives in a Cloudflare secret. Without it set, agent access is off.
function bearer(request) {
  return (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '').trim();
}

// Jayson and Alex each have a personal access code (Pages secrets KEY_JAYSON, KEY_ALEX).
const HUMANS = [['KEY_JAYSON', 'jayson'], ['KEY_ALEX', 'alex']];

async function humanFromBearer(request, env) {
  const given = bearer(request);
  if (!given) return '';
  for (const [name, who] of HUMANS) {
    if (await sameSecret(given, env[name])) return who;
  }
  return '';
}

async function validAgent(request, env) {
  return sameSecret(bearer(request), env.AGENT_API_KEY);
}

async function sameSecret(given, secret) {
  const key = String(secret || '').trim();
  if (key.length < 24 || !given) return false;
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest('SHA-256', enc.encode(given)),
    crypto.subtle.digest('SHA-256', enc.encode(key))
  ]);
  const x = new Uint8Array(a);
  const y = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

export async function onRequest({request, env}) {
  const url = new URL(request.url);
  const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
  let parts = url.pathname.replace(/^\/api\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
  let email = '';
  if (local) {
    email = 'local@localhost';
  } else if (env.ACCESS_TEAM_DOMAIN && env.ACCESS_AUD) {
    const token = request.headers.get('Cf-Access-Jwt-Assertion');
    if (token) {
      try { email = await verifyAccessJwt(token, env); } catch (e) { email = ''; }
    }
  }
  let agent = false;
  if (parts[0] === 'agent') {
    if (!(await validAgent(request, env))) return json({error: 'Bad or missing agent key.'}, 401);
    agent = true;
    email = 'agent';
    parts = parts.slice(1);
  } else {
    if (!email) email = await humanFromBearer(request, env);
    if (!email) return json({error: 'Not signed in. Enter your access code.'}, 401);
  }
  try {
    if (request.method === 'GET' && parts[0] === 'me') return json({email});
    if (request.method === 'GET' && parts[0] === 'all') return json(await getAll(env.DB, email));
    if (request.method === 'GET' && parts[0] === 'skill') return json({name: 'ducon-dashboard', file: 'SKILL.md', updated: SKILL.updated, text: SKILL.text, files: SKILL.files});
    if (request.method === 'GET' && parts[0] === 'skills') return json({skills: await listSkills(env.DB)});

    if (parts[0] === 'record' && parts.length === 3 && TABLES.has(parts[1])) {
      const table = parts[1];
      const id = parts[2];
      if (!/^[A-Za-z0-9_\-:.@+]{1,200}$/.test(id)) return json({error: 'Bad id'}, 400);
      if (request.method === 'PUT') return await put(env.DB, table, id, await request.text(), email);
      if (request.method === 'DELETE') {
        await env.DB.prepare('DELETE FROM records WHERE table_name = ?1 AND id = ?2').bind(table, id).run();
        return json({ok: true});
      }
    }

    return json({error: 'Not found'}, 404);
  } catch (e) {
    return json({error: 'Server error'}, 500);
  }
}
