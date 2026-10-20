# Cart API

All cart routes start with `/api/v1/cart/` and require an authenticated
customer, except that CORS preflight requests are handled by the CORS
middleware.

- `GET /cart/` returns the customer's items, item count, and subtotal.
- `POST /cart/` adds a product using `{"product_id": 12, "quantity": 1}`.
  Adding the same product again increases its quantity.
- `PATCH /cart/items/{cart_item_id}/` sets the item's quantity.
- `DELETE /cart/items/{cart_item_id}/` removes one item.
- `DELETE /cart/` clears the cart.
- `POST /cart/apply-promo/` validates a promo code against submitted cart lines;
  see [reviews and promos API](reviews-and-promos-api.md) for its payload and
  response.

The cart does not reserve stock. The order API checks and reserves stock when
the customer submits an order.
