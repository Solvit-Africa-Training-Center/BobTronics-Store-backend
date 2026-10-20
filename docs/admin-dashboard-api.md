# Admin dashboard API

All paths below start with `/api/v1`. These routes require an authenticated
`admin` or `super_admin` account.

## Notifications

`GET /notifications/admin/` returns a current snapshot of operational alerts:
pending orders, reviews awaiting moderation, and available products at or below
the configured low-stock threshold. The response is:

```json
{
  "count": 1,
  "results": [
    {
      "type": "pending_order",
      "title": "Order needs review",
      "message": "Order #42 is awaiting confirmation.",
      "resource_id": 42,
      "created_at": "2026-10-20T09:30:00+00:00"
    }
  ]
}
```

Alerts are generated from current records on each request; they are not stored
and do not have read/unread state.

## Reports

- `GET /reports/summary/` returns order count, non-cancelled order value, order
  counts by status, the five products with the most units sold, and the store
  currency.
- `GET /reports/export/` downloads the matching non-cancelled orders as CSV.
- Both routes accept optional `date_from=YYYY-MM-DD` and
  `date_to=YYYY-MM-DD` query parameters. The date range applies to order date.

`order_value` uses order totals and is not a payment settlement total. Payment
reporting is outside these endpoints.

## Store settings

- `GET /settings/` returns the store settings. The first request creates the
  default row if none exists.
- `PATCH /settings/` updates one or more writable fields:
  `store_name`, `contact_email`, `contact_phone`, `currency`,
  `standard_delivery_fee`, `express_delivery_fee`, and `low_stock_threshold`.
- Delivery fees must be zero or greater. Currency is a three-character code.
  The initial low-stock threshold is 5 products.

Example update:

```json
{
  "store_name": "BobTronics Store",
  "contact_email": "support@example.com",
  "currency": "RWF",
  "standard_delivery_fee": "0.00",
  "express_delivery_fee": "0.00",
  "low_stock_threshold": 5
}
```
