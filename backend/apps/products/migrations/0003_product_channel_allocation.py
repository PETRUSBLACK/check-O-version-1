from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_product_uuid_pk"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="smartmall_allocation",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text=(
                    "Optional. Reserve a specific stock quantity for SmartMall orders only. "
                    "Leave blank to use the main stock field. "
                    "Use this if you sell on multiple channels."
                ),
            ),
        ),
    ]
