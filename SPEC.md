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

Detection order (cheapest/most reliable first):
1. **Known-format regex bank** (`envelope/patterns.yaml`) — RFC 3164/5424
   syslog, ISO 8601, common vendor timestamp formats. Matched first; no
   LLM cost.
2. **LLM fallback** — an unrecognized envelope shape is sent once to an
   LLM to propose a split regex, which is then cached the same way
   ParseForge caches cli-name resolution (`naming/cache.py`): a source
   (device/app) only ever costs tokens once per distinct envelope shape.

The marker portion (facility/severity/tag, e.g. `%LINK-3-UPDOWN`) is kept
alongside the body, not discarded — it's frequently most of the signal
needed for category naming in step 3, and is retained as context in trial
metadata the same way ParseForge retains `command_info` (vendor/os/version)
per trial.

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
