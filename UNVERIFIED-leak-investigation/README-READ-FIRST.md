# Leak investigation — status: UNVERIFIED, needs a decision before acting on it

`UMBRELLA-CORE-LEAK-REPORT.md` in this folder is a report Sepiso Toni
uploaded, apparently comparing a `new_attempt/UmbrellaOS/umbrella-core`
against an `old_attempt/umbrella-core-CURRENT`. **The head chat that
packaged this project could not independently verify this report** —
it never had access to the `new_attempt` files being compared, only the
report's own text. Read it critically, not as an established fact.

## What makes this worth taking seriously rather than dismissing

The report's `old_attempt/umbrella-core-CURRENT` folder name is not a
generic label — it's the exact naming convention this project's own
head chat used for its Phase 10 deliverable packages (see
`umbrella-core-CURRENT/` in this same package, one level up). The
report's file list under "files that exist ONLY in the old backend" —
`services/moderation_intelligence/`, `services/investigation/`,
`services/knowledge/`, `services/memory/`, `registry/`, `capabilities/`,
etc. — matches this project's real, actual Phase 0–9 subsystem list,
not a fabrication. **This is consistent with the report being a real
comparison against a real copy of this project's actual backend**, not
noise. That's exactly why it deserves real verification, not exactly
why it should be assumed true.

## What a new chat should actually do with this

1. **Do not assume it's true or false — verify it.** Ask Sepiso Toni for
   the actual `new_attempt/UmbrellaOS` files (or the exact zip this
   report's `.env` finding came from) if a real side-by-side comparison
   is wanted. A report describing a diff is not the diff itself.
2. **If Sepiso Toni confirms the `new_attempt` zip is real and has
   existed outside a fully trusted environment (uploaded anywhere,
   synced, shared) — the `SECRET_KEY`/`ADMIN_KEY` values the report
   claims are real and populated should be treated as compromised and
   rotated, independent of whether the rest of the leak claim is ever
   fully confirmed.** This part doesn't need the file-comparison
   question resolved first — rotating a possibly-compromised key is
   cheap; leaving a possibly-compromised key live is not.
3. **This is a different question from the historical `UmbrellaMC`
   story** in `historical-reference/ORIGINAL-MASTER-STATUS-AND-HANDOFF-pre-phase10.md`.
   That earlier abandoned attempt is a separate, ~165MB zip that has
   never been uploaded to any chat in this project's history (explicitly
   excluded — "mostly dead weight," per that doc's own words). It was
   not available to include in this package, and conflating it with
   whatever `new_attempt/UmbrellaOS` is in this leak report would be a
   mistake — they may be entirely unrelated, or the same thing, and
   that itself is one of the things worth asking Sepiso Toni to clarify.
4. Ask Sepiso Toni directly: what is `new_attempt/UmbrellaOS`? Is it
   something they built, something someone else built, or something
   another AI tool produced? The report's own recommendation ("delete
   `files/umbrella-core` entirely... there is no file in it that's
   meaningfully second-attempt work") assumes context this package
   doesn't have — get that context before acting on the recommendation.
