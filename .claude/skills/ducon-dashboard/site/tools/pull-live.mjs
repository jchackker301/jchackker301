#!/usr/bin/env node
// Copies the live records into the LOCAL test database (behind localhost:8788), so tests use real data.
// Only the local D1 is touched. The live database is read through the agent key and never written here.
//   node tools/pull-live.mjs
// Needs DESK_URL and DESK_KEY, and `npm run db:local` run once before.
import {writeFileSync, mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

const base = (process.env.DESK_URL || '').replace(/\/$/, '');
const key = process.env.DESK_KEY || '';
if (!base || !key) {
  console.error('Set DESK_URL and DESK_KEY first.');
  process.exit(2);
}

const res = await fetch(base + '/api/agent/all', {headers: {authorization: 'Bearer ' + key}});
if (!res.ok) {
  console.error('Request failed:', res.status, await res.text());
  process.exit(1);
}
const all = await res.json();

const q = (s) => "'" + String(s).replace(/'/g, "''") + "'";
const rows = [];
for (const v of all.videos || []) rows.push(['videos', v.id, v]);
for (const e of all.events || []) rows.push(['events', e.id, e]);
for (const p of all.projects || []) rows.push(['projects', p.id, p]);
for (const p of all.shoots || []) rows.push(['shoots', p.id, p]);
for (const p of all.intel || []) rows.push(['intel', p.id, p]);
if (all.settings) rows.push(['settings', 'team', all.settings]);

const lines = ['DELETE FROM records;'];
for (const [table, id, obj] of rows) {
  const data = Object.assign({}, obj);
  delete data.id;
  lines.push('INSERT INTO records (table_name, id, data, updated_by, updated_at) VALUES (' +
    [table, id, JSON.stringify(data), 'pull-live', new Date().toISOString()].map(q).join(', ') + ');');
}

const dir = mkdtempSync(join(tmpdir(), 'desk-pull-'));
const file = join(dir, 'pull.sql');
writeFileSync(file, lines.join('\n'));
// Call wrangler through node directly: spawning npx on Windows crashes libuv when the child exits.
const wrangler = join(dirname(fileURLToPath(import.meta.url)), '..', 'node_modules', 'wrangler', 'bin', 'wrangler.js');
try {
  execFileSync(process.execPath, [wrangler, 'd1', 'execute', 'ducon-desk', '--local', '--file=' + file], {stdio: 'inherit'});
} finally {
  rmSync(dir, {recursive: true, force: true});
}
console.log('local copy ready:', (all.videos || []).length, 'videos,', (all.events || []).length, 'events,', (all.projects || []).length, 'projects,', (all.shoots || []).length, 'shoots');
