import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TrackingEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[
                    ("pending", "Pending"), ("processing", "Processing"),
                    ("packaging", "Packaging"), ("pickup", "Pickup"),
                    ("in_transit", "In transit"), ("delivered", "Delivered"),
                ], max_length=32)),
                ("note", models.TextField(blank=True)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("shipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tracking_events", to="delivery.shipment")),
                ("recorded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tracking_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "delivery_trackingevent", "ordering": ["-created_at"]},
        ),
    ]
