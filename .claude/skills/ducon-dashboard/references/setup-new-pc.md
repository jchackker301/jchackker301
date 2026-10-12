# First-time setup on a new PC

Goal: a new Claude on another PC can run, test, edit and deploy the War Room without touching the live data by accident.

## What you need
- Node.js 20 or newer (`node -v`).
- The downloaded `ducon-dashboard.zip` from the Skills room.
- Jayson's Cloudflare login (for deploy only) and the two personal codes (for the live page only).
- The agent key (`DESK_KEY`). Jayson gives it to you. Never paste it in chat or in a file that goes into git.

## Steps
1. **Install the skill.** Unzip `ducon-dashboard.zip` into the Claude skills folder, so you get `~/.claude/skills/ducon-dashboard/SKILL.md` and `references/`. Keep the `site/` folder that comes with it somewhere you can edit it, or follow step 3.
2. **Put the credentials in place.** Create `~/.claude/ducon-desk.env` with two lines:
   ```
   DESK_URL=https://ducon-content-desk.pages.dev
   DESK_KEY=<agent key from Jayson>
   ```
   Never copy this file into the site folder or into git.
3. **Get the current source.** Choose a work folder, then run from any folder that has `tools/pull-source.mjs` (the `site/` folder):
   ```bash
   node tools/pull-source.mjs <your-work-folder>
   ```
   This writes the deployed source into `<your-work-folder>/site/` (including the generated `functions/lib/skill.js`). Pick a normal folder such as `Documents\...`, never a folder inside the Windows Temp folder: local D1 fails there. Work from that copy. Use the zip's `site/` only if the live site is unreachable.
4. **Install packages.** In the site folder:
   ```bash
   npm install
   ```
5. **Log in to Cloudflare (deploy only).**
   ```bash
   npx wrangler login
   ```
   Use Jayson's Cloudflare account. Skip this if you only test locally.
6. **Local secret.** Create `.dev.vars` in the site folder with a local-only agent key of 40 or more random characters:
   ```
   AGENT_API_KEY=<40+ random characters, local only>
   ```
   This key is for localhost only. It is not the live key. Never commit `.dev.vars`.
7. **Create the local database (once).**
   ```bash
   npm run db:local
   ```
8. **Preview config.** The site folder has `.claude/launch.json` with the `ducon-desk-local` preview (port 8788). Start it with the preview tool, or run `npx wrangler pages dev public --d1=DB --port 8788`.
9. **Copy live data into the local test database.**
   ```bash
   node tools/pull-live.mjs
   ```
   Expected: 47 videos and 7 events (or the current live counts). The live database is only read.
10. **Open the local page** at `http://localhost:8788`. Localhost signs you in as `local@localhost`. Check the week, the rooms and the Skills room.

## Optional: custom skills
In the Skills room press "Download all custom (N)". Unzip it into your .claude\skills\ folder. Each folder is one skill.

## Checks that prove the setup works
- `node tools/desk.mjs all` returns JSON with videos, events and settings.
- The Skills room shows the built-in card with a working Download .zip button.
- `npm run skill:sync` prints the file count and "secrets checked" without an error.

## If something is missing
- `DESK_URL and DESK_KEY must be set`: the env file is missing or not loaded. Check step 2.
- `Bad or missing agent key`: the key is wrong or was rotated. Ask Jayson.
- `Secret ... found in the bundle`: a key value ended up in a source file. Remove it from that file, then run the sync again. Do not bypass the check.
- `wrangler` asks to log in: run step 5, or skip it if you are not deploying.
- `Could not resolve "../lib/skill.js"` when the server starts: the generated file is missing. Run `node tools/pull-source.mjs <folder>` again (it writes the file) or `npm run skill:sync`.
- `internal error` from `wrangler d1 execute --local`: the work folder is inside the Windows Temp folder. Move it to a normal folder and run the steps again.
- `/api/all` returns 500 "Server error" on localhost (found on the MARKETING.USB PC, 2026-10-12): the dev server was started with `--d1=DB`, which makes a SECOND empty local database that is not the one `npm run db:local` / `pull-live` fill. Start it with `npx wrangler pages dev public --port 8788` (no `--d1` flag) so it uses the `wrangler.toml` binding `ducon-desk`.
- npm 12 blocks install scripts: run `npm install-scripts approve workerd` and `npm install-scripts approve esbuild`, then `npm rebuild`, or wrangler will not start.
