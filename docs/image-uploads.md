# Catalog image uploads

Catalog admins upload product and category image files. External image URL
fields are no longer accepted or stored.

## Product images

Send a `multipart/form-data` request to
`POST /api/v1/catalog/admin/images/` with an admin access token. Include
`product` (the product ID) and `image_file` (the image file). You can also
include `is_primary=true`. The first image for a product becomes primary
automatically.

The response returns the uploaded file path in `image_file`; product listings
return the primary uploaded image in `primary_image`. Uploads are limited to
5 MB. To replace an uploaded image, send `PATCH` to
`/api/v1/catalog/admin/images/{image_id}/` with a new `image_file`.

## Category images

Send `multipart/form-data` to `POST /api/v1/catalog/admin/categories/` with
the category fields and `image_file`. The response returns the uploaded file
path in `image_file`.

Applying migration `0003_remove_catalog_image_urls` removes the old URL columns.
Any external image URLs stored in those columns are discarded; upload those
images as files before applying the migration if you need to keep them.

## Storage

In development, files are saved under `media/` and served at `/media/` when
`DEBUG=True`. Production media serving is not configured in this project yet.
Setting `MEDIA_ROOT` to a persistent disk preserves files, but does not itself
serve them. Production needs a media server or object-storage backend before
these image URLs can be used.
