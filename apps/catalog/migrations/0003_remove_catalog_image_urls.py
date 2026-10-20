from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_category_and_product_image_files"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="category",
            name="image",
        ),
        migrations.RemoveField(
            model_name="productimage",
            name="image_url",
        ),
    ]
