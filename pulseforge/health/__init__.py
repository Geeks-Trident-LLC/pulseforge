"""Per-category health/pulse scoring (SPEC.md §5): match rate, frequency,
and field-value distribution over time. The one stage with no ParseForge
equivalent -- ParseForge's drift.py tells you a template stopped matching;
this tells you whether a category's *behavior* looks healthy at all,
match rate included.
"""
