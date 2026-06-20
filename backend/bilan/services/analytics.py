"""
Deprecated compatibility module.

This file previously contained analytics based on legacy assumptions
(`Question`, `Annotation`, `Copy.total_score`, …) which could lead to
approximations/simulations.

For Bilan generation we MUST compute all statistics from REAL database data:
- `exams.Copy` with status FINALIZED
- `grading.Score.scores_data` (per-question points)

The reference implementation lives in `analytics_simple.py`.
"""

from .analytics_simple import DNBAnalyticsEngine  # noqa: F401
