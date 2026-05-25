from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0002_initial"),
        ("products", "0002_product_uuid_pk"),
    ]

    operations = [
        migrations.AddField(model_name="productpromotion", name="promotion_type",
            field=models.CharField(choices=[("featured","Featured Listing"),("discount","Discount"),("flash_sale","Flash Sale"),("banner","Banner Ad")], default="featured", max_length=20)),
        migrations.AddField(model_name="productpromotion", name="discount_percent",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5)),
        migrations.AddField(model_name="productpromotion", name="is_active",
            field=models.BooleanField(default=True)),
        migrations.AddField(model_name="productpromotion", name="budget",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="productpromotion", name="impressions",
            field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="productpromotion", name="clicks",
            field=models.PositiveIntegerField(default=0)),
    ]
