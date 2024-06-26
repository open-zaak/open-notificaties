# Generated by Django 2.2.2 on 2019-06-05 15:06

from django.db import migrations


def convert_to_response_status_int(apps, schema_editor):
    NotificatieResponse = apps.get_model("datamodel", "NotificatieResponse")
    for response in NotificatieResponse.objects.all():
        try:
            response.response_status_int = int(response.response_status)
            response.save()
        except ValueError:
            continue


class Migration(migrations.Migration):
    dependencies = [("datamodel", "0009_notificatieresponse_response_status_int")]

    operations = [migrations.RunPython(convert_to_response_status_int)]
