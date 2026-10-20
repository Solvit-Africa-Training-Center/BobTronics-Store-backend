from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0002_order_promo_fields")]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("processing", "Processing"),
                    ("shipped", "Shipped"),
                    ("delivered", "Delivered"),
                    ("cancelled", "Cancelled"),
                    ("failed", "Failed"),
                    ("returned", "Returned"),
                ],
                db_index=True,
                default="pending",
                max_length=30,
            ),
        ),
    ]
