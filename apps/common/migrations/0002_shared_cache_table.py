from django.core.cache import caches
from django.core.cache.backends.db import BaseDatabaseCache
from django.db import migrations, models


def create_cache_table(apps, schema_editor):
    cache = caches["default"]
    if not isinstance(cache, BaseDatabaseCache):
        return

    connection = schema_editor.connection
    if cache._table in connection.introspection.table_names():
        return

    meta = type(
        "Meta",
        (),
        {"app_label": "django_cache", "db_table": cache._table},
    )
    cache_entry = type(
        "CacheEntry",
        (models.Model,),
        {
            "__module__": __name__,
            "cache_key": models.CharField(max_length=255, unique=True, primary_key=True),
            "value": models.TextField(),
            "expires": models.DateTimeField(db_index=True),
            "Meta": meta,
        },
    )
    schema_editor.create_model(cache_entry)


class Migration(migrations.Migration):
    dependencies = [("common", "0001_store_settings")]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]
