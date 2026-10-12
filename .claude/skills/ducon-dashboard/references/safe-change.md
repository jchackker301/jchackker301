# Safe change, test and deploy

Use this for every change so other parts of the War Room do not break. It works on any PC.

## 1. Start from the live source
- Run `node tools/pull-source.mjs <work-folder>` and work in that copy, or confirm your local copy matches the live bundle date.
- Check `git status` if the folder is a repo. Keep unrelated files untouched.

## 2. Back up the file you will change
- Copy `public/index.html` (and `functions/api/[[path]].js` if the API changes) to a scratch folder with a dated name.

## 3. Make the change as an exact-match patch
- Use a small Node script that finds the old text, requires exactly one match, then replaces it. Fail loudly on zero or many matches.
- Watch line endings: the file may use CRLF. Detect it and join lines with the same ending.
- Keep the style of the surrounding code: ES5 `var`, `function`, no build step.

## 4. Test locally, before deploy
- Local page: `http://localhost:8788` (preview `ducon-desk-local`, or `npx wrangler pages dev public --d1=DB --port 8788`).
- Refresh the local copy with `node tools/pull-live.mjs` so tests use real data.
- In the browser, pass the `tabId` on every call. Run state-changing checks as one script.
- Scan every room and person view for `NaN`, `undefined`, `null`.
- Check numbers against an independent calculation from `/api/all`.
- Check that nothing overflows: no horizontal scroll, and Home still fits one screen.
- Delete every test record you created, and confirm the local data counts match the live counts again.

## 5. Lint
- Extract the page script and run ESLint 8 with `no-undef` and `no-unused-vars`, with `--env browser,es2015`. Use `npx -y eslint@8.57.0 --no-eslintrc ...`.
- `node --check` on the extracted script catches syntax errors first.

## 6. Deploy
- `npm run deploy`. It rebuilds the bundle (and stops if a secret shows up), then uploads the `public` folder and the functions.
- Wait about 10 to 15 seconds.
- Check the live page with a cache-busting query (`https://ducon-content-desk.pages.dev/?v=<random>`) for a string from your change.
- Check the live data: `node tools/desk.mjs all`. Confirm the video and event counts did not drop.

## 7. Roll back if something is wrong
- List recent deployments: `npx wrangler pages deployment list --project-name ducon-content-desk`.
- Promote the last good one in the Cloudflare dashboard (Pages, ducon-content-desk, Deployments, Rollback), or redeploy the last good copy of `public/`.
- Data is separate from code. A rollback never changes the D1 records. If records were changed by mistake, restore them from the last `pull-live` copy or the backup, and say so to Jayson.

## Lessons from building it (avoid repeating)
- A stale browser tab or the wrong `tabId` ran tests on the wrong page. Always pass `tabId`.
- Hidden or reduced-motion browser panes freeze CSS animations. Check positions with `document.getAnimations()` and set `currentTime`, not with a timer.
- A patch that moves CSS rules can change cascade order. Compare computed styles before and after a CSS merge.
- Shell quoting breaks inline JSON on Windows. Use `@file.json` with `desk.mjs`.
- Cloudflare can serve the old page for about 10 seconds after deploy. Recheck with a cache-busting query.
- Never change the live data to make a test pass. Test on the local copy.

## What to tell Jayson after a change
- What changed, in one or two lines.
- What was tested (local, numbers, lint, live string check, data count).
- What was not tested (for example the live page behind login, or the live page on a phone).
