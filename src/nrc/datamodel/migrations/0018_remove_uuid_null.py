# Generated by Django 3.2.13 on 2022-06-27 14:46
from django.db import migrations, models

from django.db import migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("datamodel", "0017_populate_uuid_values"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notificatie",
            name="uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                help_text="Unique resource identifier (UUID4)",
                unique=True,
            ),
        ),
    ]