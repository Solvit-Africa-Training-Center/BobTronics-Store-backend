from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("promotions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromoCode",
            fields=[
                ("promo_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(db_index=True, max_length=50, unique=True)),
                ("discount_type", models.CharField(choices=[("percentage", "Percentage"), ("fixed", "Fixed Amount")], max_length=20)),
                ("discount_value", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("minimum_order_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("usage_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("usage_count", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "promo_codes",
                "ordering": ["-start_date"],
            },
        ),
        migrations.AddIndex(
            model_name="promocode",
            index=models.Index(fields=["is_active", "start_date", "end_date"], name="idx_promo_active_dates"),
        ),
    ]
