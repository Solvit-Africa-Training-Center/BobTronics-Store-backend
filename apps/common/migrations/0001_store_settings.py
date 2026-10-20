from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="StoreSettings",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("store_name", models.CharField(default="BobTronics Store", max_length=120)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("contact_phone", models.CharField(blank=True, max_length=30)),
                ("currency", models.CharField(default="RWF", max_length=3)),
                (
                    "standard_delivery_fee",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                (
                    "express_delivery_fee",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=10,
                        validators=[MinValueValidator(Decimal("0.00"))],
                    ),
                ),
                ("low_stock_threshold", models.PositiveIntegerField(default=5)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "store_settings",
                "verbose_name": "Store settings",
                "verbose_name_plural": "Store settings",
            },
        ),
    ]
