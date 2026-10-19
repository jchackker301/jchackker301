---
name: reference-video-production
description: Write and revise reference-based video prompts, 2x2 storyboards and music briefs while preserving approved coverage, character identity, pronunciation and scene continuity. Apply specific user feedback without redesigning approved material.
---

# Reference-based video production

## Primary rule

Clarity first. Give explicit, concrete instructions for every decision that materially affects the requested image, action, meaning or continuity. Define the actor, exact action/state, object or gaze target, and relevant position/direction/timing from the brief, references and bible. Replace vague phrases such as “do something,” “react naturally,” or “move over there” with the actual visible action and target when those details matter. Do not leave critical staging decisions for the generator to guess.

Clarity is not invented detail: use established evidence and context. If a critical fact remains unknown, mark it unresolved and request only the information needed, while completing independent work. Do not invent reference contents, positions, causes or approvals to make a prompt look complete. Routine choices within authorized scope may be made explicitly and recorded as working decisions, never presented as user-approved facts. Include enough detail to remove material ambiguity while keeping irrelevant content out of the prompt.

### Mandatory fail-closed workflow

This order is required for every new project, scene, storyboard, video prompt, revision and media-specific request:

1. **Story bible gate:** create or update the project bible first. Record context, artifact/variant, references, geography, shot plan, dialogue, props, screen states, branding scope and open assumptions with provenance.
2. **Source and scope gate:** read the latest user instruction and selected variant. Identify the exact artifact and authorized changes. Lock all other approved decisions.
3. **Planning and continuity gate:** build the shot-state ledger and run the applicable continuity gates, including geography, observer side, camera placement, eyelines, frame contents, routes, props, phone states, knowledge and timing.
4. **Draft gate:** write a release candidate only after the first three gates pass. If a critical item remains unresolved, work only on a clearly labeled internal draft or unaffected sections; marking an issue does not make it pass. Apply the frame-local and pink-elephant rules.
5. **Post-draft gate:** run the labeled-shot, dialogue, timing, scope, minimality and difference checks. Save the review result and release status.

If the story bible or required gate review is missing, the prompt is **DRAFT BLOCKED**. Do not provide a copy-ready generation prompt as if it were final. You may provide a clearly labeled bible update, gate findings, or an unresolved-dependency report and continue independent work. A previous assistant prompt does not count as a passed gate. The user does not need to remind the assistant to run this workflow.

### Frame-local descriptions

Describe only what the camera should show in each shot's visual prompt. Naming an off-screen person as a gaze target can encourage the generator to include that person, so keep off-screen identities and spatial relationships in the internal shot ledger. Validate the eyeline there, then express only the visible gaze direction or action in the generation prompt. Use an established direction, never invent screen-left/right without camera geometry.

For example, an individual kitchen-window close-up can say: “Close-up of the son inside the kitchen. He looks out through the window. Part of the kitchen is visible behind him.” The father's location belongs in the continuity record, not this visual description. Do not append a list of excluded people or objects. Define the subject, crop and visible background positively. Keep reference identity instructions brief.

Necessary off-screen speech belongs only in the separate audio/script section, clearly assigned to its speaker. This exception does not authorize adding the speaker to the visual framing. Preserve complete internal scene knowledge for logic checks while limiting each delivered shot description to its intended visible content.

Mandatory C22 gate: compare every delivered visual shot against its internal frame manifest, remove unintended off-screen entity mentions, and rerun eyeline/side checks. Repeat the check on the assembled prompt after revisions. Any known frame-content leakage is a MAJOR failure to fix before release; record the check outcome in the artifact review.

Mandatory C24 gate: every required prop must have a positive identity specification, reference mapping, owner, hand, visible form and state. Do not use a category word as a substitute for the prop's visual form. Check the rendered prop silhouette and state separately from the action. For this project the father's prop is the reference yellow retractable tape-measure casing, fully retracted and lowered in one hand. A known wrong prop blocks release.

Describe only what belongs in the requested scene. Omit absent people, props, events and speculative alternatives. Avoid long negative lists: mentioning an unwanted object can introduce it into generated imagery. Give a short positive instruction for the intended object or action.

User corrections override earlier prompt versions. Edit the smallest necessary portion when asked to fix without changing anything. Return the complete corrected prompt when requested, rather than a patch or acknowledgement.

Standing user requirement: AI-generated videos use clean cinematic frames. Exclude text overlays, subtitles, captions, logos, watermarks, promotional graphics and branded/text end cards, including those inherited from older source prompts. Write positive output framing where sufficient rather than copying a long exclusion list into generation prompts. Preserve explicitly requested in-scene phone messages as diegetic screen content; they are not overlays. Phone UIs use plain controls without brand logos. This rule applies across projects unless the user explicitly overrides it later.

Standing language requirement: prompts and scripts use basic, literal, everyday English. Avoid slang, regional/American idioms, figurative action, double meanings, obscure vocabulary and decorative synonyms. Choose the exact simple verb for the intended action or state. Name the actor, object, destination/body part and direction when needed. For a bag already worn, write “He wears the bag over his right shoulder.” For putting it on, write “He places the bag strap over his right shoulder.” For carrying it by hand, write “He holds the bag in his right hand.” Do not substitute a static state for an intended movement or simplify away required meaning. Translate technical camera terms into simple wording when it preserves precision; retain necessary unambiguous terms such as “close-up.”

Standing eyeline rule: a character looks at the intended visible subject, object or scene action. The character looks into the camera only when the user explicitly requests a direct-to-camera look or the approved shot requires it. Do not add camera eye contact as a generic emotion cue or performance default. If the target is off-screen, keep its identity in the internal ledger and describe only the frame-local gaze/action in the visual prompt.

### Pink-elephant principle: prompt only the intended scene

Apply the user's rule: “If hindi kailangan, huwag banggitin.” Treat the pink-elephant analogy as a practical editing heuristic, not a proven explanation of model behaviour or a guarantee of generation quality.

Before delivering a generation prompt, review every noun, action and audio instruction. Retain it only if it defines requested visible content, audible content, necessary reference mapping, timing or continuity. Delete irrelevant alternatives, past mistakes, correction history and redundant explanations.

Translate exclusions into concise positive staging. Describe the desired prop, participant count, route, screen state or sound directly. Keep internal troubleshooting and rejected options out of the copy-paste prompt. Preserve explicit user requirements by expressing their intended outcome; do not silently drop constraints.

Preferred generation wording:

- Prop: “He holds the reference yellow tape-measure casing in his palm, with the tape fully retracted.”
- Voice: “Clear conversational English. Read the single dialogue block verbatim, once.”
- Listening: “She listens with relaxed, closed lips.”
- Image layout: “One portrait sheet with four equal panels arranged in two rows and two columns.”
- Family route: “They meet in the indoor hallway, then exit through the central sliding doors.”
- Submission-only ending: “End on the outgoing message.”
- Appearance: “Use the attached image as the sole appearance reference.”
- Clean frame: “Image-only cinematic frame.”

Mention characters only where they appear or their off-screen voice is required. Establish a group once and describe its continuing actions without repeatedly restating entrances. Keep speech-control instructions short and put each spoken line in one place. Use a negative instruction only when a necessary requirement cannot be communicated clearly through positive wording or the user explicitly requests it.

## Establish the current brief

### Exact-action verb rule

Always choose the simplest precise verb that names the intended action or state. Distinguish hold/carry, look/turn, walk/run, wear/put on, tap/type, raise/lower and open/close as required by the actual event. Do not use a decorative synonym or broad instruction when a concrete physical action is intended. Add actor, object, direction, destination or body part only where needed to make the movement clear. During review, verify that each action verb matches the visible event, starting state and resulting state. If the action itself is unclear from the brief, resolve it from context rather than guessing a visually different movement.

### First action for every project: establish the story bible

Before writing a storyboard or generation prompt, create or update a persistent STORY_BIBLE.md in that project's workspace directory. For an existing project, read and continue its bible rather than restarting from a remembered draft. The bible is the canonical project record; latest explicit user corrections override it and must be incorporated first. Do not treat assistant proposals as user-approved facts.

An approval applies only to the artifact, version and scope the user accepted. Praise of blocking does not approve incidental screen text, props or dialogue. User silence is not approval. If no project directory is established, create a descriptive workspace directory. If persistence is unavailable, provide a labeled working bible in the response and report that it was not saved; do not claim it exists on disk.

Record:

- Project goal, product context, audience, story premise and intended emotional arc.
- Current version and provenance of decisions: explicit user instruction, user-approved source, observed reference detail, or provisional assumption.
- Reference IDs and character-role mapping; appearance comes from references.
- Location geography, routes, starting positions and character relationships.
- Approved beat and shot IDs, duration, format, camera coverage, context, blocking, action and expression.
- Exact dialogue in one canonical block, speaker assignments, pronunciation and language rules.
- Prop ownership and state, phone ownership, screen requests/results and physical-scene continuity.
- Approved branding/end-card scope, audio direction and required deliverables.
- Open questions and provisional details, kept separate from locked decisions.
- A concise change log stating what changed, why, which user instruction authorized it and which artifacts are affected.

Keep superseded choices in the history only. Do not feed historical alternatives into generation prompts. Save reusable project-specific facts in the project bible rather than allowing one project's choices to silently become another project's defaults.

### Stability and change control

For every revision, follow `references/revision-procedure.md`. Revisions are scoped patches to a known artifact, not automatic rewrites or automatic approvals of earlier assistant drafts.

Treat user-approved choices as locked. A request to fix pronunciation, a prop or one line authorizes that edit and its necessary dependent corrections, not a new storyline, new framing or rewritten ending. Derive every deliverable from the same bible version. Reuse approved wording where it still applies; do not rewrite for novelty.

Update the bible before revising dependent prompts, and identify outdated artifacts when a change affects them. Preserve distinct approved variants with names and scopes instead of silently merging them. An assumption can support progress but must remain labeled provisional. Ask only when a material contradiction prevents a useful correct result.

### Mandatory review gates

Run two separate review passes before delivering any storyboard or prompt. These are internal quality gates, not user approval requests.

PASS 1 — BEFORE DRAFTING

1. Source gate: read the current bible and latest user request. Resolve which version and artifact are being revised. Check reference availability and decision provenance.
2. Scope gate: identify exactly what the user authorized to change. Lock everything else and record any necessary dependent updates.
3. Planning gate: ensure the story, duration, shot count, geography and dialogue can fit together before drafting. Identify missing or contradictory prerequisites.

PASS 2 — AFTER DRAFTING

4. Continuity gate: compare every shot and line against the bible. Apply the continuity and logic gates in `references/continuity-gates.md` to each shot and every adjacent shot pair. Record applicable outcomes, evidence and unresolved issues; a checklist alone is not proof of a pass.
5. Direction gate: verify context, framing, blocking, action and facial expression are clear and physically compatible with each shot. Compare storyboard and video coverage by shot ID.
6. Speech and timing gate: check basic English, one dialogue block, each line once, correct speaker and phonetic spelling, sufficient speaking time and exact runtime arithmetic.
7. Clarity, minimality and literal-language gate: verify each material action's actor, exact verb, target and relevant position/direction/timing in the internal plan. In the delivered visual prompt include only subjects and details intended to appear in that frame; express off-screen targeting through visible gaze direction where needed. Flag unresolved critical facts instead of guessing. Apply the pink-elephant edit. Remove unnecessary appearance descriptions, unwanted alternatives and repetitive instructions. Check prompts and dialogue for slang, idioms, figurative verbs, double meanings and unnecessarily difficult vocabulary. Preserve intended meaning and necessary visible scene details.
8. Change gate: compare the final draft with the previous approved version. Every change must trace to the current request or a necessary consistency correction. Revert unrelated edits.

If a gate fails, correct the draft and repeat the affected checks before delivery. A genuine unresolved blocker should be named specifically; do not claim the prompt is verified or error-free. These gates verify prompt consistency, not the future generator's output. Keep the user-facing response focused on the requested artifact rather than dumping the internal checklist.

Apply the release rules and save the review record described in `references/release-review.md`. Evidence must refer to the exact artifact being delivered. A changed artifact invalidates affected passes; a changed shot boundary also invalidates its adjacent transitions. Never report a gate as executed merely because its instructions exist.

For continuity review, keep a shot-state ledger with start/end positions, body orientation, gaze target, visibility, prop ownership, screen state, character knowledge and elapsed story time. Distinguish world coordinates from screen directions and character-relative directions. Update only affected records when revising. Run a separate output review after generation; planned continuity does not establish observed continuity.

For peeking or threshold shots, apply C21 explicitly: character side, camera side, target side and gaze direction are separate facts. A camera outside the house does not place the observer outside. Preserve the character's zone until an authorized crossing, and check actual reference/output cues before certifying the physical setup.

Track the requested artifact (storyboard, beat video, full film, revision, or music analysis), duration, shot count, approved coverage, reference assignments, props, dialogue and screen contents. Resolve these from conversation before asking questions. Never silently change the duration or storyline to make a prompt fit.

Latest scene-specific instructions take priority. For example, an earlier ban on showing generated designs does not apply to a later explicitly requested design-reveal scene. Do not repeat superseded restrictions.

## Reference identity and continuity

- Let supplied references define faces, age, ethnicity, body, clothing, accessories, phones and architecture.
- Assign references by role; a location reference supplies architecture, not character identity.
- With supplied character references, omit appearance descriptions altogether unless explicitly requested. Identify people by role and reference only. Direct camera, action, eyeline and expression without redescribing faces, demographics or clothing.
- Direct acting through small movements, eyelines and restrained expressions. Extreme expressions can weaken likeness.
- Preserve approved camera angles, shot order, separate reaction coverage and spatial relationships unless a revision explicitly changes them.
- If identity drifts in a multi-panel generation, recommend generating shots individually and assembling the approved images without regeneration. Reference likeness is not guaranteed by prompt wording alone.

## Storyboards

When the user requests a vertical 2x2 sheet, specify:

“One portrait 9:16 sheet, four equal panels in a 2x2 grid. Reading order: top-left, top-right, bottom-left, bottom-right.”

Use the labels TOP-LEFT, TOP-RIGHT, BOTTOM-LEFT and BOTTOM-RIGHT exactly. Each panel describes a single visible moment with framing, action and expression. Do not add dialogue lettering, decorative captions, logos or unrequested panels. Do not confuse a storyboard grid with the sequential shots of the finished video.

Keep storyboard and video coverage synchronized. Do not invent a three-phone group result shot to fill a fourth panel when the approved video has three independent send/result inserts. Use the fourth panel for an existing approved action or result moment and preserve its chronological position in the matching video prompt.

## Video prompts

Use this proportional structure:

1. Beat name, exact duration, aspect ratio and shot count.
2. A short reference and continuity instruction.
3. Timed shots covering context, framing, blocking, action and facial expression; reference the single dialogue block when needed.
4. Short voice, sound and transition instructions.

For an approved ten-second, four-shot beat, preserve that structure. A 2.5-second allocation per shot is a default only when timing is not already approved. Avoid instructions that contradict the shot framing: an off-frame prop need not be forced into a face close-up.

Every video prompt must establish these five directing elements clearly, using short, basic English:

- Context: where the scene happens and what the character wants or has just noticed.
- Framing and camera placement: explicitly identify camera location/zone, boundary side when relevant, facing direction, height/angle, shot size and movement. Distinguish camera position from character position. Use approved geography and references; do not invent an unrelated setup or change locked coverage. Apply C23.
- Blocking: starting position, direction of movement, eyeline and relationship to other visible people or objects.
- Action: a concrete, physically performable sequence that fits the allotted time.
- Facial expression: a small visible response that communicates the intended emotion, without redescribing facial features.

Keep all five elements consistent with the reference and approved shot. For a hands-only or object insert, express intent through the visible action and carry facial expression in the adjacent character shot; do not add a face or change framing just to fill a template. Shared context can be stated once and inherited by the shots.

### Required labeled shot format

Use explicit labels for each shot/panel, including revisions. Scale the wording to the task, not the presence of the labels. Fill from the brief, bible and references; routine authorized camera choices are working specifications, not claims about reference EXIF.

```
SHOT ID / TIME:
CONTEXT:
CAMERA LOCATION:
CAMERA DIRECTION:
CAMERA HEIGHT / ANGLE:
LENS:
FRAMING:
CAMERA MOVEMENT:
BLOCKING:
ACTION:
EMOTION:
FACIAL EXPRESSION:
SCRIPT / SPEECH:
```

CONTEXT states the immediate event/purpose relevant to the visible subject, briefly. Keep off-screen cast and causal background in the internal ledger unless required for separate audio. BLOCKING states visible starting position and movement path; ACTION uses exact simple verbs. EMOTION describes intent, and FACIAL EXPRESSION gives a concrete visible cue. For an insert with no visible face, use “FACIAL EXPRESSION: Not applicable to this crop” in the internal record and omit that label from the generation text rather than adding a person; retain the other applicable labels. Put spoken words once in the separate audio block.

SCRIPT / SPEECH is required for every shot. If there is no spoken audio, state “No dialogue. Not talking.” This brief explicit silence instruction is requested by the user and is allowed under the positive-prompting rule. If a visible character speaks, identify the speaker and dialogue ID; keep the actual line only in the single audio block. If speech continues off-screen, state “Off-screen dialogue continues: D02. Visible character listens silently.” Define the speaker and exact words under D02 in the audio block. Distinguish silent visible acting from absence of all speech; do not write “No dialogue” over an intended off-screen line. For a fully silent clip, the SCRIPT / SPEECH label suffices without an empty dialogue block.

Give LENS a focal length when requested or useful, such as “50 mm, full-frame equivalent.” Use a consistent sensor/equivalent convention. Check field of view against subject distance, physical room, framing and camera position; a focal length alone does not determine shot size. Preserve approved perspective. Avoid assigning an exact distance or source lens as an observed fact without evidence. Keep optical specifications concise and recognize that generator adherence must be checked in output. Use the same specification if a continuous setup is inherited.

Before release, verify that every applicable label is filled, mutually consistent and frame-local. Check SCRIPT / SPEECH against audible dialogue and visible mouth actions. Missing critical context, camera geometry, blocking, action or speech state fails preflight; fix or flag it instead of filling it with vague wording. Do not let template completeness override the pink-elephant rule.

Use plausible actions and routes. A character hidden at a window should not climb through it or acquire an invented door. Their transition may occur off-camera. Keep hand-held props consistent across shots.

Read project routes and arrival actions from the selected bible variant. Examples in this skill are illustrative, not default staging for a new project.

## Dialogue and pronunciation

- Use basic everyday English for dialogue and prompt instructions. Keep voice direction to “Clear, natural English.” Omit accent terminology from generation prompts altogether, including negative or neutral-accent instructions. Character nationality must not become a voice instruction.
- Use English-only dialogue, including “Dad” instead of “Baba.” Prefer familiar short words, direct sentences and one thought per line. Apply the standing literal-language requirement to both speech and action directions. Avoid tongue twisters, alliteration and dense consonant sequences. Preserve approved meaning; if a locked exact line conflicts with a later simplicity instruction, revise only its wording and recheck timing and intended meaning.
- Put all spoken lines in exactly one dialogue block. Do not duplicate them in shot descriptions, split them into quoted fragments across cuts, or repeat trigger words in lengthy speech-control instructions. Use silent pauses between lines.
- When a user reports repeated speech artifacts, simplify the audio brief and test one targeted change. Do not claim that prompt complexity or a particular word boundary is the verified cause without evidence. Persistent failures call for a controlled recorded-dialogue and lip-sync workflow, not increasingly long prohibition lists.
- Use short, natural lines that fit the available speaking time. Estimate approximately 2–2.5 words per second, leaving room for reactions and pauses.
- If the approved line is too long, continue the same voice over reaction shots where appropriate. If that is insufficient, flag the timing issue rather than promising fluent delivery at an impossible pace.
- Identify the speaker explicitly. A voice continuing off-screen remains the same speaker; listeners remain silent.
- Keep a sentence continuous across picture cuts. In shot descriptions refer to dialogue IDs or “the same line continues”; put its words only in the dialogue block.
- Read the approved spoken spelling and visible spelling separately from the project bible. A pronunciation correction does not automatically authorize changing visible branding. Explicit user instructions for both take precedence.
- Never invent official brand pronunciation. Confirm it or preserve approved wording.
- Request fluent delivery, natural pauses, clear articulation and synchronized lips without guaranteeing that a generator cannot stutter or mispronounce.
- Suggest recorded dialogue and lip-sync only as an optional precision workflow; still supply the requested video prompt.

## Phones and design concepts

Tie each insert to its owner's reference. Avoid restating appearance details already supplied by the reference. Associate each request and result with its owner through shot IDs and the project bible.

Specify the attached image using the project's approved source scene. Keep source photo, request text, returned concept and physical environment as separate states.

If the scene shows submissions only, end each insert on the outgoing send action. If the approved scene shows results, associate each concept with its owner and keep the physical location unchanged. Do not carry an outgoing-only restriction into an explicitly requested result reveal.

Read request wording, result scope and interface state from the project bible. When a source image shows an already-sent message but the next action is a send tap, first prepare a ready-to-send starting image or flag that dependency; do not promise both exact preservation and a contradictory screen state. Budget photo/request reading, tapping, transition and result hold separately. If state changes are compressed by an edit, preserve shot-count conventions and do not imply guaranteed service speed. For still-image edits, correct garbled UI text when authorized rather than treating it as exact required text.

Use a plain messaging interface and the standing clean-frame rule. Earlier approval of source footage or an end card does not override the user's newer global exclusion. If removing an old end card leaves unused time, use an existing compatible scene hold within authorized scope; flag any need for a new creative ending rather than silently inserting one.

## Props

Read prop identity, reference, owner, hand and state from the project bible. Describe the intended prop positively and consistently. Track hand occupancy and explain acquisitions, placements or transfers through plausible actions.

## Music reverse engineering

Inspect the uploaded audio itself before describing its sound. First discover available audio playback/perception and analysis capabilities. Check duration and encoding, then audition if supported. When possible, assess tempo, metre, instruments, rhythmic pattern, harmony, texture, dynamics, transitions and the mix beneath dialogue.

Separate directly heard observations, measured estimates and uncertain interpretations. Speech, effects and short clips can distort tempo estimates. Metadata and waveform inspection alone cannot establish instruments or genre. Preserve uncertainty and identify the analyzed time range.

If direct audition is unavailable, perform useful supported analysis and state its limits. Do not substitute the advertisement's intended mood for the actual soundtrack, claim to have listened, or label a generic music prompt as a reverse-engineered result. Offer an approximation only with explicit labeling. Never claim to identify the exact track without evidence.

## Final check

Before returning a prompt, check that it:

- Matches the requested beat and artifact, duration, shot count and grid format.
- Preserves approved coverage and latest corrections.
- Describes only visible or audible scene content.
- Passes the pink-elephant edit: every included concept serves the requested result, and unnecessary alternatives and repeated correction language have been removed.
- Uses reference-based identity instructions without unnecessary recasting descriptions.
- Gives dialogue enough time and keeps speaker assignments and pronunciation consistent.
- Keeps prop, screen, physical-location and character continuity coherent.
- Makes no unsupported claims about audio, generation fidelity or completed work.

## Persistence

Capture reported failures and tested corrections using `references/learned-errors.md`. Consult relevant project entries before drafting. Treat user preferences as requirements, but causal explanations as hypotheses until supported by comparative evidence. Do not promote an adopted correction to a proven fix merely because it was saved in this skill.

This file is a reusable workspace skill, not model retraining or automatic cross-session memory. Report where it was saved. Do not claim global installation or future automatic activation unless the host has actually registered it.
