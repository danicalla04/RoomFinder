from django.db import migrations


def enable_accounts_without_email_verification(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="customer").update(is_active=True)
    User.objects.filter(role="owner", owner_approval_status="approved").update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_user_owner_approval_status")]

    operations = [
        migrations.RunPython(enable_accounts_without_email_verification, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="email_verified_at"),
        migrations.RemoveField(model_name="user", name="email_verification_nonce"),
        migrations.RemoveField(model_name="user", name="email_verification_sent_at"),
        migrations.RemoveField(model_name="user", name="email_verification_attempts"),
    ]
