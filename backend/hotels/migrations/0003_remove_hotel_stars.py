from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("hotels", "0002_calapan_city_only"),
    ]

    operations = [
        migrations.RemoveField(model_name="hotel", name="stars"),
    ]
