# Reviews and promo validation API

All paths below are under `/api/v1`.

## Reviews

- `GET /reviews/` lists approved reviews. Use `?product={product_id}` to filter.
- `GET /reviews/{feedback_id}/` retrieves one approved review.
- `POST /reviews/` lets an authenticated customer submit `product`, `rating`
  (1–5), and optional `comment`. New reviews start as `pending` and are hidden
  from public reads until an admin approves them.
- `GET /reviews/admin/` lists all reviews for an admin, with optional `status`,
  `product`, and `rating` filters.
- `GET /reviews/admin/{feedback_id}/` returns a review and its moderation status.
- `PATCH /reviews/admin/{feedback_id}/` accepts `{"status":"approved"}` or
  `{"status":"hidden"}`. `DELETE` on that path permanently removes a review.

Admin routes require an admin or super-admin account. Public review responses
include `feedback_id`, `product`, `author`, `rating`, `comment`, and
`created_at`. Admin responses additionally include `user`, `user_email`,
`product_name`, `status`, and `updated_at`.

## Promo validation

`POST /cart/apply-promo/` validates a promo against current product prices.
`POST /cart/promo/` is an alias for clients already using that path. Both
require an authenticated customer.

Request:

```json
{
  "code": "WELCOME10",
  "items": [
    {"product_id": 12, "quantity": 2}
  ]
}
```

The backend reads prices and availability from the database. A valid response
contains `valid`, `code`, `discount_type`, `discount_value`, `subtotal`,
`discount_amount`, and `total`. Invalid or expired codes return `valid: false`
and a customer-facing message. This endpoint calculates a quote; it does not
reserve promo usage or create an order, so checkout must validate again.

Admins create promo codes in Django admin under Promo Codes. Percentage values
must not exceed 100. Set dates, minimum spend, and optional usage limit there.
