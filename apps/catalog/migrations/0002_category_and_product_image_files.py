from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="image_file",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="category-images/%Y/%m/",
            ),
        ),
        migrations.AlterField(
            model_name="productimage",
            name="image_url",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="productimage",
            name="image_file",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="product-images/%Y/%m/",
            ),
        ),
    ]
