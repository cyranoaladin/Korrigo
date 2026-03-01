"""
Map Patrick's old localStorage UUIDs to new DB copy UUIDs via anonymous_id.
Run inside Django shell on the server.
"""
import json
from exams.models import Copy

# Load reconstitution data
with open('/app/reconstitution_data_v2.json', 'r') as f:
    data = json.load(f)

copies_data = data.get('copies', [])

# Old UUIDs from Patrick's localStorage extraction
old_uuids = [
    '68a19865-3a81-40a8-89c4-983636bf52a4',
    '994bdea9-0f4e-404e-ad14-0b7749d442c9',
    '745d9f7f-64ed-4cde-9ea1-cab8b8a77aab',
    'e1350746-e2b9-4cf2-b3da-9d1d9d382748',
    '6fe4f5a4-fa03-42d1-92aa-2eb66a90f26f',
    'dc3ad9a5-eb5b-4f21-9c10-ea8e83d14fe2',
    '20efc1c4-f2fa-4be0-9f9b-fe00b5fb195d',
    '3923b78e-c791-49e6-bced-0c4c8ea78edd',
    '2070208b-c5a8-4fe6-b5b8-61b13b550dd0',
    '9127f151-d98e-4d20-8c40-738132e4e67d',
    '043ea249-452a-4cf3-969d-09899aa241da',
    '0a3826c4-23dc-4e30-bae4-0c61bf1faf58',
    'a5bd614d-f5b7-4e66-abf8-2239fefd59c8',
    '2b1b2bee-062e-4694-9b23-3aa78783b848',
    '4d5d3210-bd11-4cd1-85ce-d77b2e0f8665',
    'd719ae31-c5d7-45f6-b4ec-8051f21c1d4e',
    'fff58503-361f-419f-b1d2-aa8b9d343a85',
    '34a7cbe6-3722-4d8c-ba4e-c18b526b8928',
    'c9160eaa-26be-44e6-ab9f-5834c7e16e42',
    '33b11d02-1439-4d52-9d71-b84cc34ec92a',
    '9278e168-bbf7-4856-9def-96be84815745',
    '15112593-e922-4dfb-81b7-b577c801ea10',
    'f8d7b32c-a320-4483-8f0b-768a2da259ba',
    'ee5996fc-cdb5-40d9-a15d-d83b316a2582',
    '72e9c336-1d27-4ed8-8b1b-0da0efa1b8d4',
    '765bff7e-16be-4c55-a442-951fe3065090',
]

# Build index: old_uuid -> copy info from dump
old_index = {}
for c in copies_data:
    old_index[str(c.get('id', ''))] = c

print(f"Reconstitution data: {len(copies_data)} copies")
print(f"Patrick localStorage: {len(old_uuids)} old UUIDs")
print()
print(f"{'OLD UUID':<40} {'ANON_ID':<12} {'NEW UUID':<40} {'STATUS'}")
print("-" * 135)

mapped = 0
not_found_dump = 0
not_found_db = 0

for old_uuid in old_uuids:
    if old_uuid in old_index:
        info = old_index[old_uuid]
        anon_id = info.get('anonymous_id', '?')
        new_copy = Copy.objects.filter(anonymous_id=anon_id).first()
        if new_copy:
            print(f"{old_uuid}  {anon_id:<12} {str(new_copy.id):<40} {new_copy.status}")
            mapped += 1
        else:
            print(f"{old_uuid}  {anon_id:<12} {'DB NOT FOUND':<40}")
            not_found_db += 1
    else:
        print(f"{old_uuid}  {'NOT IN DUMP':<12}")
        not_found_dump += 1

print()
print(f"=== RESULTAT: {mapped} mapped, {not_found_dump} not in dump, {not_found_db} not in DB ===")
