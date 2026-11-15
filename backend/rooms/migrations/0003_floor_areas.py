from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("rooms", "0002_measured_floor_plan")]

    operations = [
        migrations.AddField(
            model_name="floor", name="areas",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
