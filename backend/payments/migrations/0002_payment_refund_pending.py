from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[
                    ("approved", "Deposit simulated"),
                    ("refund_pending", "Refund pending"),
                    ("refunded", "Refunded"),
                ],
                default="approved",
                max_length=14,
            ),
        ),
    ]
