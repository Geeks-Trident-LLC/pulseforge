# PulseForge

`pulseforge` is an AI-driven pipeline that categorizes, templates, and
health-scores unstructured log streams — turning a raw log line into a
named category, a validated parsing template, and an ongoing health
signal, without reimplementing the template-forging machinery
[ParseForge](https://github.com/Geeks-Trident-LLC/parseforge) already
provides.

## How it works

1. **Envelope splitting** — separates a log line's
   `<date-time-marker>` from its `<log-body>` (a known-format regex bank
   first, an LLM fallback for anything unrecognized).
2. **Category naming** — an LLM names a log body's category
   (`link-updown`, `bgp-neighbor-down`, ...), cached so a given body
   shape is only ever sent to the LLM once.
3. **Template forge** — delegates straight to ParseForge's own
   trial → integration → promotion pipeline, treating a category the way
   ParseForge treats a cli-name.
4. **Parsing** — applies a category's authoritative template to new log
   bodies.
5. **Pulse (health) scoring** — tracks match rate, frequency, and
   field-value distribution per category over time, flagging
   inconsistency — the one stage with no ParseForge equivalent.

## Status

Scaffold only. Directory layout and module boundaries are in place;
every pipeline stage is currently a stub (`NotImplementedError`).
Nothing here is wired end to end yet — see the repo's
[README](https://github.com/Geeks-Trident-LLC/pulseforge#status) for
what's real versus planned.

## Explore further

- [SPEC](https://github.com/Geeks-Trident-LLC/pulseforge/blob/main/SPEC.md) — full design plan
- [ParseForge](https://github.com/Geeks-Trident-LLC/parseforge) — the template-forging engine this project delegates to
