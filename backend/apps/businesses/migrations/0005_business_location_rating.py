import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0004_business_uuid_pk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BusinessLocation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(default="Nigeria", max_length=100)),
                ("full_address", models.TextField(blank=True)),
                ("business", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="location", to="businesses.business")),
            ],
            options={"db_table": "businesses_location"},
        ),
        migrations.CreateModel(
            name="BusinessRating",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("score", models.PositiveSmallIntegerField()),
                ("review", models.TextField(blank=True)),
                ("business", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="businesses.business")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="business_ratings", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "businesses_rating", "unique_together": {("business", "customer")}},
        ),
    ]
