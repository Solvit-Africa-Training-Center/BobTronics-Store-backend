# Wishlist API

All routes start with `/api/v1/wishlist/` and require an authenticated
customer.

- `GET /wishlist/` returns the customer's saved products.
- `POST /wishlist/` saves a product with `{"product_id": 12}`. Saving an
  already saved product is safe and returns the existing item.
- `DELETE /wishlist/{product_id}/` removes that product from the customer's
  saved list.

Unavailable products cannot be added. Product list responses include the
primary uploaded image URL when one exists.
