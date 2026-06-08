import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("businesses", "0006_business_category"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Menu",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(default="Menu", max_length=255)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("business", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="menu", to="businesses.business")),
            ],
            options={"db_table": "dining_menu"},
        ),
        migrations.CreateModel(
            name="MenuSection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("menu", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="dining.menu")),
            ],
            options={"db_table": "dining_menu_section", "ordering": ["position", "name"]},
        ),
        migrations.CreateModel(
            name="MenuItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("image", models.ImageField(blank=True, null=True, upload_to="dining/menu_items/")),
                ("is_available", models.BooleanField(default=True)),
                ("dietary_flags", models.JSONField(blank=True, default=list)),
                ("preparation_minutes", models.PositiveSmallIntegerField(default=15)),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="dining.menusection")),
            ],
            options={"db_table": "dining_menu_item", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Reservation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("date", models.DateField()),
                ("time", models.TimeField()),
                ("party_size", models.PositiveSmallIntegerField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("completed", "Completed"), ("no_show", "No Show")], default="pending", max_length=20)),
                ("special_requests", models.TextField(blank=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("business", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reservations", to="businesses.business")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dining_reservations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "dining_reservation", "ordering": ["-date", "-time"]},
        ),
    ]
