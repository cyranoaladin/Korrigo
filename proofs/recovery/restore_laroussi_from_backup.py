#!/usr/bin/env python3
"""
Restore Laroussi's scores from backup 20260302_230001.

Problem: fix_laroussi_scores.py (23h17) incorrectly overwrote the REAL scores
that Laroussi had entered via the API (28q including 4.1.3) with the old
localStorage scores (27q, without 4.1.3).

Timeline:
  11h17 - ls_recovery imported localStorage scores (27q) for 052-072
  14h44-15h25 - Laroussi re-corrected ALL copies via API (28q), adding 4.1.3
                and modifying individual question values. Also corrected 073-075
                directly via API (never in localStorage).
  23h17 - fix_laroussi_scores.py incorrectly overwrote API scores with localStorage
  23h25 - THIS SCRIPT: restored all 21 copies (052-072) from backup 23h00
          + restored 075FB-073 (MAAREF YOUNES) from backup (was 2q→27q)

Source of truth: backup 20260302_230001/copies_data.json (made at 23h00,
captures the real API-entered scores before our destructive fix)

Result: 22 copies restored to match backup exactly.
  - 052-072: 28q (with 4.1.3), real totals from Laroussi's API session
  - 073: 27q, total=16.50 (Laroussi completed via API, not in localStorage)
  - 074-075: untouched (never affected by fix, scored directly via API)
  - 076: READY, 5q (in progress)
  - 077: READY, no score (not started)

Verification: 0 differences between DB and backup for all 26 Laroussi copies.
"""
# Script was executed directly on server via docker exec.
# See fix_laroussi_scores.py for the incorrect fix that necessitated this restore.
