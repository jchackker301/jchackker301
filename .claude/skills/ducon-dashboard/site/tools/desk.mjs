#!/usr/bin/env node
// Agent CLI for the Ducon Editor's War Room. Needs DESK_URL (site origin) and DESK_KEY (the AGENT_API_KEY secret).
//   node tools/desk.mjs all
//   node tools/desk.mjs put videos v1 '{"title":"Pool villa","tier":"A","status":"idea","assignee":"Jayson","editDeadline":"2026-10-17"}'
//   node tools/desk.mjs put events m1 '{"title":"Site visit","eta":"2026-10-14T15:00","who":"Both","value":"High"}'
//   node tools/desk.mjs del videos v1

import {readFileSync} from 'node:fs';

const base = (process.env.DESK_URL || '').replace(/\/$/, '');
const key = process.env.DESK_KEY || '';
if (!base || !key) {
  console.error('Set DESK_URL and DESK_KEY first.');
  process.exit(2);
}

const [cmd, table, id, rawBody] = process.argv.slice(2);
// Pass JSON inline, or "@file.json" to read it from a file (easier on Windows shells).
const body = rawBody && rawBody.startsWith('@') ? readFileSync(rawBody.slice(1), 'utf8') : rawBody;

async function call(method, path, payload) {
  const res = await fetch(base + '/api/agent' + path, {
    method,
    headers: {authorization: 'Bearer ' + key, ...(payload ? {'content-type': 'application/json'} : {})},
    body: payload
  });
  const text = await res.text();
  if (!res.ok) {
    console.error(res.status, text);
    process.exit(1);
  }
  return text;
}

if (cmd === 'all') console.log(await call('GET', '/all'));
else if (cmd === 'put' && table && id && body) console.log(await call('PUT', `/record/${table}/${encodeURIComponent(id)}`, body));
else if (cmd === 'del' && table && id) console.log(await call('DELETE', `/record/${table}/${encodeURIComponent(id)}`));
else if (cmd === 'skills') console.log(await call('GET', '/skills'));
else {
  console.error('Usage: all | skills | put <videos|events|projects|shoots|intel|settings|skills> <id> <json> | del <table> <id>');
  process.exit(2);
}
