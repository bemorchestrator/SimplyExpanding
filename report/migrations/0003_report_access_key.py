import uuid
from django.db import migrations, models

# Function to generate access keys for existing reports
def generate_access_keys(apps, schema_editor):
    Report = apps.get_model('report', 'Report')  # Get the Report model
    for report in Report.objects.all():
        report.access_key = str(uuid.uuid4())  # Generate a unique access key for each report
        report.save()

class Migration(migrations.Migration):

    dependencies = [
        ('report', '0002_report_report_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='access_key',
            field=models.CharField(default=uuid.uuid4, max_length=64, unique=True),
        ),
        migrations.RunPython(generate_access_keys),  # Run the function to generate keys
    ]
