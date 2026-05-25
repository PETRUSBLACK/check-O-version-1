import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIConversation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assistant_type", models.CharField(choices=[("customer", "Customer Shopping Assistant"), ("vendor", "Vendor Business Assistant")], default="customer", max_length=20)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("history", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ai_conversation", "ordering": ["-updated_at"]},
        ),
    ]
