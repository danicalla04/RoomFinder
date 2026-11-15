from django.db import migrations, models
from django.core.validators import MinValueValidator


def fit_legacy_rooms(apps, schema_editor):
    Floor = apps.get_model("rooms", "Floor")
    Room = apps.get_model("rooms", "Room")
    for floor in Floor.objects.using(schema_editor.connection.alias).all():
        rooms = Room.objects.using(schema_editor.connection.alias).filter(floor_id=floor.pk)
        max_column = max((room.column + 1 for room in rooms), default=0)
        max_row = max((room.row + 1 for room in rooms), default=0)
        floor.plan_width_m = max(30, max_column * 5)
        floor.plan_height_m = max(20, max_row * 5)
        floor.save(update_fields=["plan_width_m", "plan_height_m"])


class Migration(migrations.Migration):
    dependencies = [
        ("rooms", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="floor", name="plan_width_m",
            field=models.DecimalField(decimal_places=2, default=30, max_digits=6),
        ),
        migrations.AddField(
            model_name="floor", name="plan_height_m",
            field=models.DecimalField(decimal_places=2, default=20, max_digits=6),
        ),
        migrations.AddField(
            model_name="room", name="plan",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.RunPython(fit_legacy_rooms, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="room", name="area",
            field=models.DecimalField(decimal_places=2, default=28, max_digits=7, validators=[MinValueValidator(1)]),
        ),
    ]
