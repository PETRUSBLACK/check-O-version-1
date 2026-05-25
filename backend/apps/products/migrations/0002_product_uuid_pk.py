import uuid
from django.db import migrations, models


def populate_product_uuids(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    for obj in Product.objects.filter(uuid_id__isnull=True):
        obj.uuid_id = uuid.uuid4()
        obj.save(update_fields=["uuid_id"])


class Migration(migrations.Migration):
    """
    Convert Product primary key from BigAutoField to UUIDField.
    Uses Python-level population — works on SQLite (dev) and PostgreSQL (prod).
    """

    dependencies = [
        ("products", "0001_initial"),
        ("businesses", "0004_business_uuid_pk"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="uuid_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(populate_product_uuids, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(model_name="product", name="id"),
        migrations.RenameField(model_name="product", old_name="uuid_id", new_name="id"),
        migrations.AlterField(
            model_name="product",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
    ]
