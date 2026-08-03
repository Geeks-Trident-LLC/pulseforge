# PulseForge

AI-driven pipeline that turns unstructured log streams into categorized,
templated, health-scored signal — a sibling project to
[ParseForge](https://github.com/Geeks-Trident-LLC/parseforge), reusing its
trial → integration → promotion template pipeline instead of
reimplementing it.

Full design plan: [SPEC.md](SPEC.md).

## Why

CLI-command output ("show interface status") and log-body messages
("%LINK-3-UPDOWN: Interface ... changed state to down") are both just
"unstructured text that recurs in a small number of shapes and needs a
template." ParseForge already solves the hard part of that problem —
LLM-drafted templates, self-validated against their own sample,
clustered by output schema, and promoted only once they clear a match-rate
gate, with a human-reviewed path for anything short of it. PulseForge
applies that same machinery to log messages, and adds the two things logs
need that CLI output doesn't:

- **Envelope splitting** — a log line isn't one blob, it's a
  `<date-time-marker>: <log-body>` pair. The marker has to be split off
  before anything downstream (naming, templating) sees clean body text.
- **Category naming instead of command naming** — there's no fixed
  command vocabulary to resolve against; an AI has to look at a log body
  and name its type (`LINK-3-UPDOWN`) before a template can even be
  requested for it.
- **Pulse (health) scoring** — once a category has an authoritative
  template, PulseForge tracks its match-rate, frequency, and field-value
  distribution over time and flags when a category goes unhealthy or
  inconsistent — not just "the template broke" (drift), but "this
  category's behavior looks wrong."

## Architecture

```
ingestion -> envelope split -> category naming -> template forge (delegates
to parseforge) -> parse -> pulse/health scoring -> sink
```

See [SPEC.md](SPEC.md) for the full breakdown of each stage.

## Status

Scaffold only. Directory layout and module boundaries are in place;
pipeline stages are stubs (`NotImplementedError`) pending real
implementation. Nothing here is wired end to end yet.

## Installation

```bash
# local development
pip install -e ".[dev,sampling]"
```

## Relationship to ParseForge

PulseForge depends on `parseforge` as an ordinary pip package — the
template-forging stage (`pulseforge/forge/adapter.py`) calls straight into
`parseforge.api` rather than forking or copying its pipeline. A PulseForge
"category" is passed into that pipeline the same way ParseForge's own CLI
resolves and passes a "cli-name": as the key a group of samples is
generated, validated, and promoted under.
