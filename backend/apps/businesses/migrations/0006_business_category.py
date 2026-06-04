from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0005_business_location_rating"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="category",
            field=models.CharField(
                choices=[
                    ("retail", "Retail Shop"),
                    ("grocery", "Grocery / Supermarket"),
                    ("restaurant", "Restaurant / Food"),
                    ("hotel", "Hotel / Lodging"),
                    ("pharmacy", "Pharmacy"),
                    ("fashion", "Fashion / Clothing"),
                    ("electronics", "Electronics"),
                    ("beauty", "Beauty / Salon"),
                    ("health", "Health / Fitness"),
                    ("education", "Education / Training"),
                    ("automobile", "Automobile / Auto Parts"),
                    ("other", "Other"),
                ],
                default="retail",
                max_length=50,
                help_text="Primary category of this business.",
            ),
        ),
    ]
