# Site fragments — verbatim preserved bands from earlier sessions

These files preserve, **byte for byte**, the hand-maintained H57-scarpstep band that the
2026-10-07 H57 session placed at the top of `index.html` and `submission.html` (merged to
`main` via PRs #22/#23). That session edited the generated pages directly instead of extending
the site generator, which broke the repository's reproducibility invariant
(`build_h55_site.py` no longer reproduced the committed pages — `checks-and-site` failed on
`main`).

`scripts/build_h58_site.py` inserts these fragments (after verifying the H57-scarpstep
artifact's SHA-256 against its committed evidence `evidence/build_h57-scarpstep.json`) and
then adds this session's H58 band, so the whole site is generated again and the
`git diff --exit-code` CI check passes. The fragments are their session's presentation,
preserved verbatim — including its claims, which are that session's, not this one's. This is
recorded as an irregularity: the H57-scarpstep band is *not* generated from machine-readable
evidence the way every other band on this site is.

- `h57-scarpstep-index-band.html` — the `<section class="main" id="h57">` download band from
  `index.html` (verbatim).
- `h57-scarpstep-submission-band.html` — the `<section class="main" id="h57">` submission band
  from `submission.html` (verbatim).
