from django.db import migrations


PEER_REVIEW_STATUS_CONSTRAINT_SQL = """
ALTER TABLE public.grading_peerreviewcorrection
DROP CONSTRAINT IF EXISTS check_peer_review_status_valid;

ALTER TABLE public.grading_peerreviewcorrection
ADD CONSTRAINT check_peer_review_status_valid
CHECK (
    ((status)::text = ANY (
        ARRAY[
            ('NOT_STARTED'::character varying)::text,
            ('IN_PROGRESS'::character varying)::text,
            ('FINALIZED'::character varying)::text
        ]
    ))
);
"""


def reconcile_peer_review_status_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(PEER_REVIEW_STATUS_CONSTRAINT_SQL)


class Migration(migrations.Migration):

    dependencies = [
        ("grading", "0027_peerreviewcorrection_peerreviewevent_and_more"),
    ]

    operations = [
        migrations.RunPython(
            reconcile_peer_review_status_constraint,
            reverse_code=reconcile_peer_review_status_constraint,
        ),
    ]
