# PulseForge — Design Plan

Companion to [ParseForge's SPEC.md](https://github.com/Geeks-Trident-LLC/parseforge/blob/main/SPEC.md).
This document only covers what's *different* about applying that pipeline to
log messages instead of CLI output — it assumes ParseForge's trial →
integration → promotion model as a given, not something reinvented here.

## 1. Pipeline stages

```
ingestion -> envelope split -> category naming -> template forge (parseforge)
          -> parse -> pulse/health scoring -> sink
```

| Stage | Module | New here, or delegated? |
|---|---|---|
| Ingestion | `pulseforge/ingestion/` | New (file + ssh/cmdline backends) |
| Envelope split | `pulseforge/envelope/` | New |
| Category naming | `pulseforge/naming/` | New prompt/cache logic; reuses `textfsm-ai`'s multi-provider call primitive, not parseforge's cli-name-specific naming |
| Template forge | `pulseforge/forge/adapter.py` | **Delegated** — calls `parseforge.api` directly |
| Parse | `pulseforge/parsing/` | New (thin: apply an authoritative TextFSM template) |
| Pulse/health | `pulseforge/health/` | New |
| Sink | (part of `pipeline.py`) | New (structured output only, no storage/search of its own) |

## 2. Envelope splitting

A raw line is `<date-time-marker><separator><log-body>`, e.g.:

```
Aug  3 09:15:01.123: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/24, changed state to down
└──────── envelope ────────┘        └──────────────────── body ────────────────────────────┘
```

PulseForge is an AI assistant, not a CLI power-tool that assumes its user
already knows what format their own logs are in — so envelope resolution
has to support both a user who can name their format and one who can't.
Two entry paths, one shared final step:

```
                     raw lines (ingestion)
                            │
              user declares format? ──yes──┐
                            │               │
                            no              │
                            │               │
                     Auto-detect (§2.2)     │
                            │               │
                     Confirm & persist ◄────┘
                            │
              Invoke pattern from patterns.yaml,
              split every line (§2.4)
```

### 2.1 Path A — format already known

Skip detection entirely: the user (or config) names a `patterns.yaml`
entry directly (CLI: `--format rfc5424`; a `formats list` command surfaces
known names in plain language, e.g. "RFC 5424 — modern syslog, timestamps
like `2003-10-11T22:14:15.003Z`", not just the RFC number) and resolution
goes straight to §2.4. Zero regex-bank scan, zero LLM cost.

### 2.2 Path B — format unknown (auto-detect)

Layered cheapest-first, same cost-avoidance principle as `naming/cache.py`
elsewhere in this pipeline:

1. **Known-format regex bank** (`envelope/patterns.yaml`) — matched
   against a small sample of the source's own lines first, no LLM cost.
   Starting with **RFC 5424 only**: its fixed-width, unambiguous grammar
   (explicit year+timezone in TIMESTAMP, single-token HOSTNAME, bracketed
   STRUCTURED-DATA) makes it the one format worth hand-writing a precise
   pattern for up front. RFC 3164 (BSD syslog) is deliberately deferred —
   its 15-character fixed-width TIMESTAMP has no year or timezone field,
   so a naive regex silently misparses HOSTNAME/TAG the moment a sender
   stuffs either one in (see worked examples in project history); it's
   added as its own regex-bank entry only once a real request needs it,
   rather than guessing its edge cases ahead of need. If exactly one
   pattern in the bank clears a high match-rate bar (e.g. ≥90% of the
   sample), treat it as detected and proceed to §2.3; if none clears it,
   or more than one plausibly does, go to step 2.
2. **LLM fallback** — send the sample to an LLM asking it to identify a
   known format or propose a split pattern. Never trusted blind: whatever
   it proposes is re-scored against the sample exactly the way step 1
   scores a known pattern, mirroring ParseForge's self-validation
   discipline (a generated answer only counts once it's checked against
   real data, not because an LLM said so).

### 2.3 Confirm & persist

For a non-technical user, a label ("detected: RFC 5424") isn't
verification — a preview is. Show 2–3 of the user's own lines split into
columns (timestamp | body) and ask for confirmation before proceeding,
regardless of whether the match came from step 1 (high-confidence
auto-match) or step 2 (LLM-proposed, then validated).

Once confirmed, cache the resolved format against that source (same
self-caching pattern as `naming/cache.py`) so a later run against the same
source skips detection entirely and goes straight to §2.4. If step 2
produced a pattern for a shape genuinely new to `patterns.yaml`, it's a
candidate for promotion into the regex bank as its own named entry —
gated on human review, same "nothing gets promoted without evidence"
philosophy ParseForge uses for templates — so the next *different* source
with the same log shape benefits from step 1 instead of re-paying for an
LLM call.

### 2.4 Invoke

Shared final step for both paths: load the resolved `patterns.yaml` entry
and run every line through `split_envelope()`. The marker portion
(facility/severity/tag, e.g. `%LINK-3-UPDOWN`) is kept alongside the body,
not discarded — it's frequently most of the signal needed for category
naming in step 3, and is retained as context in trial metadata the same
way ParseForge retains `command_info` (vendor/os/version) per trial.

### 2.5 Non-goal (v1): mixed-format sources

§2.2's sampling assumes one dominant envelope format per source. A single
log file aggregating multiple distinct formats (e.g., merged from several
upstream systems) is out of scope for v1 — it would need per-line rather
than per-sample detection, which is a real design change (cost profile,
caching granularity), not a small extension. Revisit if a real source
actually needs it, rather than building for a hypothetical one now.

## 3. Category naming

Unlike ParseForge, there's no fixed command vocabulary to resolve against —
an AI has to look at a log body (plus its marker, if any) and assign a
category name, e.g. `link-updown`, `bgp-neighbor-down`, `auth-failure`.

Naming convention mirrors ParseForge's cli-name rules (SPEC.md §2 there):
lowercase, hyphenated, literal tokens kept, variable spans elided —
`Interface GigabitEthernet1/0/24, changed state to down` names the same
way regardless of which interface. Two log bodies that only differ in
their variable spans must resolve to the same category; two that differ
in fixed structure must not silently collide.

Self-caching: once a body shape's category is resolved, matching is regex
against the cache, not another LLM call — same free-lookup property
ParseForge's naming index has for repeated commands.

## 4. Storage layout

Mirrors ParseForge's `trials/` → `integration/` → `authoritative/`
three-tier promotion (see ParseForge SPEC.md §3), with `<cli-name>` swapped
for `<category>`:

```
<source>/<category>/
```

e.g. `cisco-ios/link-updown/`. No per-device-model segment the way
ParseForge's path includes `<vendor>/<device-family>/<os>/` — log body
shape is generally OS/version-independent for a given category; where it
legitimately isn't, that's exactly what integration's schema-clustering
step is for (same rationale ParseForge SPEC.md §3 gives for omitting a
`<version>` segment).

Trial samples, integration groups, and authoritative templates for a
category are produced and stored by calling into `parseforge.api`
unmodified — `pulseforge/paths.py` only adds the `health/` tier described
next, which ParseForge has no equivalent of.

## 5. Pulse (health) scoring

New tier, `health/<category>/`, populated once a category has an
authoritative template. Tracked per category, per time window:

- **Match rate** — fraction of new samples the authoritative template
  still parses. A sustained drop feeds back into ParseForge's drift
  pipeline as a new trial (reusing `parseforge.drift`), same as ParseForge
  already does for CLI templates.
- **Frequency** — rate of occurrence vs. its historical baseline (a
  category that suddenly fires 50x more/less often is itself a signal,
  independent of whether the template still matches).
- **Field-value distribution** — for the fields the template extracts,
  whether values are landing in their expected range/set (e.g. an
  interface-state field suddenly emitting a value never seen before).

Output is a per-category health score plus an inconsistency flag, not a
pass/fail — it's meant to be read by whatever alerting/dashboard system
already exists downstream (see §6), not to replace it.

## 6. Non-goals

PulseForge does not:
- Store or index logs long-term (that's Splunk/ELK/Loki/etc.'s job).
- Provide alerting, dashboards, or a query language.
- Replace ParseForge's CLI-output pipeline — it's a sibling application of
  the same engine to a different input shape.

Its output (structured records + per-category health score) is meant to be
emitted into whichever of those systems the business already runs.
