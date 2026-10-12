# Ducon Editor's War Room (Cloudflare)

Team dashboard for Jayson and Alex. Static page in `public/`, API in `functions/api/`, data in a Cloudflare D1 database.
Jayson and Alex sign in with email (Cloudflare Access). Claude and other agents use `/api/agent/...` with a secret key.

## Run locally (no account needed)
```
npm install
npm run db:local
npm run dev        # http://localhost:8788
```
Local mode signs you in as `local@localhost`. Agent key for local tests goes in `.dev.vars` (`AGENT_API_KEY=<40+ random chars>`), never commit it.

## Deploy (you do the Cloudflare login)
1. Create a free account at https://dash.cloudflare.com.
2. `npx wrangler login` (a browser window opens, you sign in).
3. `npx wrangler d1 create ducon-desk`, then paste the printed `database_id` into `wrangler.toml`.
4. `npm run db:remote` (creates the table).
5. `npx wrangler pages project create ducon-content-desk --production-branch main`
6. `npm run deploy` (prints the live `https://....pages.dev` URL).
7. Agent key: make a random string of 40+ characters, then `npx wrangler pages secret put AGENT_API_KEY --project-name ducon-content-desk` and paste it. Keep the key private.

## Personal access codes (current login)
Jayson and Alex each have a code stored as Pages secrets `KEY_JAYSON` and `KEY_ALEX` (copies in `C:\Users\jayso\.claude\ducon-desk.env`).
The page asks for the code once and keeps it in that browser. "Sign out" (bottom right) clears it.
To change a code: `npx wrangler pages secret put KEY_JAYSON --project-name ducon-content-desk`, then `npm run deploy`.

## Optional: Cloudflare Access instead of codes
1. Cloudflare dashboard > Zero Trust (free plan) > Access > Applications > Add an application > Self-hosted.
2. Application domain: your `....pages.dev` host. Policy: Allow, emails = Jayson's and Alex's addresses. Login method: One-time PIN.
3. Open the application and copy its **Application Audience (AUD) tag**. Your team domain is `<team-name>.cloudflareaccess.com`.
4. Set both as Pages variables:
   `npx wrangler pages secret put ACCESS_AUD --project-name ducon-content-desk`
   `npx wrangler pages secret put ACCESS_TEAM_DOMAIN --project-name ducon-content-desk`
5. Agents cannot do the email login. Add a second Access application for the path `<your host>/api/agent` with a **Bypass** policy. The agent key is the lock for that path.
6. Preview deployments (`*.pages.dev` branch URLs) are also covered by the API refusing without a valid Access token.

## Agent access
```
set DESK_URL=https://<your host>
set DESK_KEY=<the agent key>
node tools/desk.mjs all
node tools/desk.mjs put videos v1 @video.json
node tools/desk.mjs put events m1 @mission.json
node tools/desk.mjs del videos v1
```
Tables: `videos`, `events` (scheduled missions and recurring events), `settings` (id `team`).
The API refuses a save when a field is wrong (it answers 400 with the reason), so a typo cannot hide a record.

Video fields: `title` (text, required), `tier` (A Full AI | B Mix | C Normal), `kind` (project|other), `status` (idea|theme|ready|prod|done), `assignee` (Jayson|Alex|""), `owner`, `editor`, `postDate`, `editDeadline`, `slotDate`, `deliveredAt`, `readyAt` (all YYYY-MM-DD or ""), `theme`, `brief`, `desc`, `revisions`, `wildcard`, `swap`, `manual` (true skips the kickoff gate), `gate {goal,audience,product,message,cta,platform,postdate,refs,approver}`, `appr {concept,storyboard,rough}`.
`slotDate` makes a video count for that day's mandatory slot (Mon B, Tue C, Wed B, Thu C, Fri B, Sat A) whatever its tier.
Mission fields: `title`, `type` (pictorial|shoot|visit|event|meeting|other), `place`, `notes`, `eta` (YYYY-MM-DDTHH:MM), `who` (Both|Jayson|Alex), `value` (High|Medium|Low), `done` (true|false).
Recurring events add `recurring: true` and `next` (YYYY-MM-DD); they show in Missions, not in the incoming list.

## The page
Seven rooms: Home, Calendar, Inventory, Board, Missions, Reports, Skills. One week (Monday to Sunday) is shared by the week arrows, the daily slot bars, God's eye view and the calendar status.
Reports downloads an Excel (.xlsx) file or a printable page for the boss.

## Skills room and the portable skill
- The built-in `/ducon-dashboard` skill is bundled at build time (`tools/sync-skill.mjs`, run by `npm run deploy`). Download .zip gives the skill files and this whole site source. No keys are in it: the build stops if a secret value shows up in a bundled file.
- "Download all custom (N)" in the Skills room gives one .zip with every custom skill as `<name>/SKILL.md`.
- Custom skills live in the `skills` table (id = name, fields `text` and `description`). Add them in the room, or with `node tools/desk.mjs put skills <name> @skill.json`. `node tools/desk.mjs skills` lists them.
- Setup on another PC: see `references/setup-new-pc.md` inside the skill. Short version: unzip, `node tools/pull-source.mjs <folder>`, `npm install`, `npm run db:local`, `node tools/pull-live.mjs`.
- Test copy with live data: `node tools/pull-live.mjs` (writes only the local database).

## Not done yet
- Excel import (export works).
- Not tested against real Cloudflare Access or a deployed D1. Local tests passed: read, write, delete, agent key, forged header rejected.
