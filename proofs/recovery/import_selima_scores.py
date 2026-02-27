"""
Import Selima's recovered scores from localStorage into the Korrigo DB.
Run inside Django shell on the server:
    docker exec -i docker-backend-1 python manage.py shell < import_selima_scores.py

Recovery source: selima.klibi@ert.tn Chrome localStorage (2026-02-27)
- 27 valid copies with 33 questions each
- 14 NEW scores (lost copies), 1 UPDATE (0F8E-080: 18.15->18.40), 12 SKIP (identical)
- 2 duplicate UUIDs + 1 null entry excluded
"""
import json
import os
from exams.models import Copy
from grading.models import Score
from django.contrib.auth import get_user_model

User = get_user_model()

# Selima's user
selima = User.objects.get(email='selima.klibi@ert.tn')
print(f"Corrector: {selima.email} (id={selima.id})")

# Load mapping and scores from JSON files
BASE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '/app'
# When piped via docker exec, files are at known path
MAPPING_PATH = '/tmp/selima_uuid_mapping.json'
SCORES_PATH = '/tmp/selima_scores.json'

with open(MAPPING_PATH) as f:
    OLD_TO_ANON = json.load(f)
with open(SCORES_PATH) as f:
    RECOVERED_SCORES = json.load(f)

print(f"Loaded {len(OLD_TO_ANON)} UUID mappings, {len(RECOVERED_SCORES)} score sets")

# ==============================
DRY_RUN = True  # SET TO False FOR LIVE IMPORT
# ==============================

print(f"\n{'='*60}")
print(f"MODE: {'DRY RUN' if DRY_RUN else '*** LIVE IMPORT ***'}")
print(f"{'='*60}\n")

created = 0
updated = 0
skipped = 0
errors = 0

for old_uuid, scores_data in RECOVERED_SCORES.items():
    anon_id = OLD_TO_ANON.get(old_uuid)
    if not anon_id:
        print(f"ERROR: No mapping for {old_uuid}")
        errors += 1
        continue

    copy = Copy.objects.filter(anonymous_id=anon_id).first()
    if not copy:
        print(f"ERROR: No copy found for {anon_id}")
        errors += 1
        continue

    # Check if copy is assigned to Selima
    if copy.assigned_corrector_id != selima.id:
        print(f"WARNING: {anon_id} assigned to user {copy.assigned_corrector_id}, not Selima ({selima.id})")

    # Calculate total
    total = round(sum(v for v in scores_data.values() if isinstance(v, (int, float))), 2)
    nq = len([v for v in scores_data.values() if isinstance(v, (int, float))])

    # Check existing score
    existing = Score.objects.filter(copy=copy).first()
    if existing:
        if existing.scores_data:
            old_total = round(sum(v for v in existing.scores_data.values() if isinstance(v, (int, float))), 2)
            old_nq = len([v for v in existing.scores_data.values() if isinstance(v, (int, float))])
        else:
            old_total = 0
            old_nq = 0

        diff = round(total - old_total, 2)
        if abs(diff) < 0.01 and nq == old_nq:
            print(f"  {anon_id}: SKIP (identical dump={old_total} ls={total} {nq}q)")
            skipped += 1
        else:
            print(f"  {anon_id}: UPDATE dump={old_total}({old_nq}q) -> ls={total}({nq}q) diff={diff:+.2f}")
            if not DRY_RUN:
                existing.scores_data = scores_data
                existing.save()
            updated += 1
    else:
        print(f"  {anon_id}: CREATE total={total} ({nq}q)")
        if not DRY_RUN:
            Score.objects.create(copy=copy, scores_data=scores_data, final_comment='')
        created += 1

print(f"\n{'='*60}")
print(f"RESULTS ({'DRY RUN' if DRY_RUN else 'LIVE'}):")
print(f"  Created: {created}")
print(f"  Updated: {updated}")
print(f"  Skipped: {skipped}")
print(f"  Errors:  {errors}")
print(f"  Total:   {created + updated + skipped + errors}/{len(RECOVERED_SCORES)}")
print(f"{'='*60}")
if DRY_RUN:
    print("\nThis was a DRY RUN. Set DRY_RUN = False to actually import.")
