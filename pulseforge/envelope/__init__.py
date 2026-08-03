"""Splits a raw log line into its date-time-marker envelope and log-body
(SPEC.md §2). The only stage upstream of everything else — naming and
templating both operate on the body this produces, never the raw line.
"""
