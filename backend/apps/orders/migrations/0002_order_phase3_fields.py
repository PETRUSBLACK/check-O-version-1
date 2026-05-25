import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import apps.orders.models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
        ("products", "0002_product_uuid_pk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="fulfilment_type",
            field=models.CharField(
                choices=[("delivery", "Home Delivery"), ("pickup", "Pick Up In Store")],
                default="delivery",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_address",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="order",
            name="pickup_code",
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name="order",
            name="pickup_deadline",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending_payment", "Pending payment"),
                    ("paid", "Paid"),
                    ("processing", "Processing"),
                    ("packaging", "Packaging"),
                    ("shipped", "Shipped"),
                    ("delivered", "Delivered"),
                    ("cancelled", "Cancelled"),
                    ("ready_for_pickup", "Ready for pickup"),
                    ("collected", "Collected"),
                    ("expired", "Expired"),
                ],
                default="draft",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="StockReservation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantity", models.PositiveIntegerField()),
                ("expires_at", models.DateTimeField()),
                ("confirmed", models.BooleanField(default=False)),
                ("released", models.BooleanField(default=False)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reservations", to="orders.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reservations", to="products.product")),
            ],
            options={"db_table": "orders_stockreservation"},
        ),
    ]
