from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reviews", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="feedback",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("hidden", "Hidden"),
                ],
                db_index=True,
                default="approved",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="feedback",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("hidden", "Hidden"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
    ]
