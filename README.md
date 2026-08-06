# PulseForge

AI-driven pipeline that turns unstructured log streams into categorized,
templated, health-scored signal — a sibling project to
[ParseForge](https://github.com/Geeks-Trident-LLC/parseforge), reusing its
trial → integration → promotion template pipeline instead of
reimplementing it.

Full design plan: [SPEC.md](https://github.com/Geeks-Trident-LLC/pulseforge/blob/main/SPEC.md).

## What is PulseForge?

Logs — from network devices, servers, applications — are just lines of
unstructured text: a timestamp, then a message body whose shape depends
entirely on whatever produced it. Turning that into something you can
actually act on means answering the same three questions for every
distinct kind of line: what category of event is this, what does a
well-formed instance of it look like structurally, and is this category
behaving normally right now?

PulseForge answers all three. It splits a log line's timestamp from its
message body, has an AI name the body's category, forges and validates a
parsing template for that category — by delegating to
[ParseForge](https://github.com/Geeks-Trident-LLC/parseforge)'s own
trial → integration → promotion pipeline rather than reimplementing it —
and then tracks that category's match rate, frequency, and field values
over time to flag when it starts behaving inconsistently.

## Why do you need PulseForge?

Any team running nontrivial infrastructure ends up staring at a firehose
of log lines it can't parse, categorize, or trust: whoever wrote the
software chose the message formats, not you, and nobody hands you a
parser for every one of them. So teams either write and maintain regex by
hand for every log type they care about — the same tedious, brittle work
ParseForge already replaces for CLI output — or they give up and treat
logs as a search index instead of structured signal, which means "is this
category of event healthy right now" stays a question a human has to
answer by eyeballing a dashboard, if anyone thinks to ask it at all.

PulseForge turns that firehose into per-category structured data and an
ongoing health signal, automatically, with the same human-in-the-loop
review guarantees ParseForge already provides for CLI parsing.

## Features

- **Envelope splitting** — a log line isn't one blob, it's a
  `<date-time-marker>: <log-body>` pair. The marker has to be split off
  before anything downstream (naming, templating) sees clean body text.
- **Category naming instead of command naming** — there's no fixed
  command vocabulary to resolve against; an AI has to look at a log body
  and name its type (`LINK-3-UPDOWN`) before a template can even be
  requested for it.
- **Delegated template forging, not reinvented.** Template generation,
  self-validation, schema clustering, and promotion all come straight from
  ParseForge's own pipeline — a PulseForge category is passed through it
  exactly the way ParseForge passes a cli-name.
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

See [SPEC.md](https://github.com/Geeks-Trident-LLC/pulseforge/blob/main/SPEC.md) for the full breakdown of each stage.

## Installation

```bash
# local development
pip install -e ".[dev,sampling]"
```
