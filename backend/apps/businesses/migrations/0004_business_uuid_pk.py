import uuid
from django.db import migrations, models


def populate_business_uuids(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")
    for obj in Business.objects.filter(uuid_id__isnull=True):
        obj.uuid_id = uuid.uuid4()
        obj.save(update_fields=["uuid_id"])


class Migration(migrations.Migration):
    """
    Convert Business primary key from BigAutoField to UUIDField.
    Uses Python-level population — works on SQLite (dev) and PostgreSQL (prod).
    """

    dependencies = [
        ("businesses", "0003_vendor_verification_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="uuid_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(populate_business_uuids, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(model_name="business", name="id"),
        migrations.RenameField(model_name="business", old_name="uuid_id", new_name="id"),
        migrations.AlterField(
            model_name="business",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
    ]
