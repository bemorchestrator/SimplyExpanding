# Generated by Django 5.1.1 on 2024-10-10 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0016_alter_uploadedfile_avg_time_on_page'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadedfile',
            name='losing_traffic',
            field=models.CharField(choices=[('up', 'Up'), ('down', 'Down'), ('none', 'None')], default='none', max_length=10),
        ),
    ]