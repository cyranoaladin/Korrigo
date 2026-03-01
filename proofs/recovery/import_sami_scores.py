"""
Import/update Sami's recovered scores from localStorage into the Korrigo DB.
Run inside Django shell on the server.

Problem: 15/26 copies are missing exercise 4 scores in DB.
The localStorage has complete data (27 questions) for all 26 copies.
Strategy: update all scores with localStorage data (which is more complete).
"""
import json
from exams.models import Copy
from grading.models import Score
from django.contrib.auth import get_user_model

User = get_user_model()

sami = User.objects.get(email='sami.bentiba@ert.tn')
print(f"Corrector: {sami.email} (id={sami.id})")

# Load data files
with open('/tmp/sami_recovery_data.json') as f:
    recovery_data = json.load(f)
OLD_TO_ANON = recovery_data['old_to_anon']

with open('/tmp/sami_localstorage.json') as f:
    RECOVERED_SCORES = json.load(f)

print(f"Mapping: {len(OLD_TO_ANON)} entries")
print(f"Scores: {len(RECOVERED_SCORES)} entries")

# ==============================
DRY_RUN = False  # LIVE IMPORT
# ==============================

print(f"\n{'='*60}")
print(f"MODE: {'DRY RUN' if DRY_RUN else '*** LIVE IMPORT ***'}")
print(f"{'='*60}\n")

created = 0
updated = 0
skipped = 0
errors = 0

for old_uuid, scores_data in sorted(RECOVERED_SCORES.items(), key=lambda x: OLD_TO_ANON.get(x[0], '')):
    anon_id = OLD_TO_ANON.get(old_uuid)
    if not anon_id:
        print(f"ERROR: No mapping for {old_uuid}")
        errors += 1
        continue

    copy = Copy.objects.filter(anonymous_id=anon_id).first()
    if not copy:
        print(f"ERROR: No copy for {anon_id}")
        errors += 1
        continue

    if copy.assigned_corrector_id != sami.id:
        print(f"WARNING: {anon_id} assigned to {copy.assigned_corrector_id}, not Sami ({sami.id})")

    local_total = round(sum(v for v in scores_data.values() if isinstance(v, (int, float))), 2)
    local_nq = len(scores_data)
    local_ex4 = len([k for k in scores_data if k.startswith('4')])

    existing = Score.objects.filter(copy=copy).first()
    if existing and existing.scores_data:
        db_nq = len(existing.scores_data)
        db_total = round(sum(v for v in existing.scores_data.values() if isinstance(v, (int, float))), 2)
        db_ex4 = len([k for k in existing.scores_data if k.startswith('4')])

        if local_nq > db_nq:
            added_keys = set(scores_data.keys()) - set(existing.scores_data.keys())
            print(f"  {anon_id}: UPDATE {db_nq}q->{local_nq}q | {db_total}->{local_total}/20 | +{len(added_keys)} keys (ex4: {db_ex4}->{local_ex4})")
            if not DRY_RUN:
                existing.scores_data = scores_data
                existing.save()
            updated += 1
        elif local_nq == db_nq and scores_data == existing.scores_data:
            print(f"  {anon_id}: IDENTICAL {db_nq}q | {db_total}/20")
            skipped += 1
        else:
            print(f"  {anon_id}: UPDATE (same count but diff data) {db_nq}q->{local_nq}q | {db_total}->{local_total}/20 | ex4: {db_ex4}->{local_ex4}")
            if not DRY_RUN:
                existing.scores_data = scores_data
                existing.save()
            updated += 1
    else:
        print(f"  {anon_id}: CREATE {local_nq}q | {local_total}/20")
        if not DRY_RUN:
            Score.objects.create(copy=copy, scores_data=scores_data, final_comment='')
        created += 1

print(f"\n{'='*60}")
print(f"RESULTS ({'DRY RUN' if DRY_RUN else 'LIVE'}):")
print(f"  Created:  {created}")
print(f"  Updated:  {updated}")
print(f"  Skipped:  {skipped}")
print(f"  Errors:   {errors}")
print(f"  Total:    {created + updated + skipped + errors}")
print(f"{'='*60}")
if DRY_RUN:
    print("\nSet DRY_RUN = False to actually import.")
