import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0001_initial"),
        ("businesses", "0005_business_location_rating"),
    ]

    operations = [
        # Add tier and feature fields to SubscriptionPlan
        migrations.AddField(model_name="subscriptionplan", name="tier",
            field=models.CharField(choices=[("free","Free"),("starter","Starter"),("growth","Growth"),("pro","Pro")], default="free", max_length=20)),
        migrations.AddField(model_name="subscriptionplan", name="max_products",
            field=models.PositiveIntegerField(default=10)),
        migrations.AddField(model_name="subscriptionplan", name="max_promotions",
            field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name="subscriptionplan", name="featured_listing",
            field=models.BooleanField(default=False)),
        migrations.AddField(model_name="subscriptionplan", name="analytics_access",
            field=models.BooleanField(default=False)),
        migrations.AddField(model_name="subscriptionplan", name="priority_support",
            field=models.BooleanField(default=False)),
        migrations.AddField(model_name="subscriptionplan", name="is_active",
            field=models.BooleanField(default=True)),
        # Add UUID pk to SubscriptionPlan
        migrations.AddField(model_name="subscriptionplan", name="uuid_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True)),
        migrations.RunPython(
            lambda apps, se: [
                type("o", (), {"uuid_id": uuid.uuid4(), "save": lambda s, **kw: None})
                for obj in apps.get_model("subscriptions", "SubscriptionPlan").objects.filter(uuid_id__isnull=True)
                for _ in [setattr(obj, "uuid_id", uuid.uuid4()), obj.save(update_fields=["uuid_id"])]
            ],
            reverse_code=migrations.RunPython.noop,
        ),
        # Update VendorSubscription — replace active/renews_at with status/started_at/expires_at
        migrations.AddField(model_name="vendorsubscription", name="status",
            field=models.CharField(choices=[("active","Active"),("expired","Expired"),("cancelled","Cancelled"),("pending","Pending Payment")], default="pending", max_length=20)),
        migrations.AddField(model_name="vendorsubscription", name="started_at",
            field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="vendorsubscription", name="expires_at",
            field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="vendorsubscription", name="auto_renew",
            field=models.BooleanField(default=True)),
        migrations.AddField(model_name="vendorsubscription", name="cancelled_at",
            field=models.DateTimeField(null=True, blank=True)),
    ]
