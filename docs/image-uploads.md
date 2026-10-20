# Catalog image uploads

Catalog admins can upload product and category images instead of storing an
external image URL. Existing URL-based records continue to work.

## Product images

Send a `multipart/form-data` request to
`POST /api/v1/catalog/admin/images/` with an admin access token. Include
`product` (the product ID) and `image_file` (the image file). You can also
include `is_primary=true`. The first image for a product becomes primary
automatically.

The response keeps the existing `image_url` field and returns the uploaded
image URL there. Uploads are limited to 5 MB. To replace an uploaded image,
send `PATCH` to `/api/v1/catalog/admin/images/{image_id}/` with a new
`image_file`.

## Category images

Send `multipart/form-data` to `POST /api/v1/catalog/admin/categories/` with
the category fields and `image_file`. The response keeps the existing `image`
field and returns the uploaded image URL there. Existing category image URLs
remain supported.

## Storage

In development, files are saved under `media/` and served at `/media/` when
`DEBUG=True`. In production, set `MEDIA_ROOT` to the mount path of a persistent
disk or configure durable object storage. A container's default filesystem can
be cleared during redeploys, which would remove locally stored uploads.
