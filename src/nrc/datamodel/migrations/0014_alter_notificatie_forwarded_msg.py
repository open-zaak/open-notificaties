# Generated by Django 3.2.12 on 2022-03-25 10:36

import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("datamodel", "0013_auto_20200207_1344"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notificatie",
            name="forwarded_msg",
            field=models.JSONField(
                encoder=django.core.serializers.json.DjangoJSONEncoder
            ),
        ),
    ]
