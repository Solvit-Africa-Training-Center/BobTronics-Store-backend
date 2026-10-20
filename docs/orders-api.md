# Orders API

All routes are under `/api/v1/orders/`. Customer routes require an authenticated
customer. Admin routes require an admin or super-admin account.

## Create an order

`POST /orders/` creates a pending order, records item price snapshots, reserves
stock, and creates a pending delivery. It does not start or record a payment.

```json
{
  "shipping_address": "12 Example Street, Kigali",
  "phone": "+250780000000",
  "delivery_method": "standard",
  "promo_code": "WELCOME10",
  "items": [
    {"product_id": 12, "quantity": 1}
  ]
}
```

Each product may appear once. Product prices are taken from the database when
the order is created. Delivery fees come from store settings. If any item is
unavailable or out of stock, the order is not created and no stock is changed.
`promo_code` is optional; when provided, it is revalidated and its usage is
recorded only if the order is created. The response includes `promo_code` and
`promo_discount_amount` alongside the final `total_amount`. Cart entries for
the ordered products are removed after successful order creation.

## Read and cancel orders

- `GET /orders/` lists the customer's own orders.
- `GET /orders/{order_id}/` returns one of the customer's orders and its items.
- `POST /orders/{order_id}/cancel/` cancels a pending order and restores its
  stock. Other order states cannot be cancelled through this customer action.

## Admin order management

- `GET /orders/admin/` lists orders; filter by `status` or `user`.
- `GET /orders/admin/{order_id}/` returns the order and customer email.
- `PATCH /orders/admin/{order_id}/` accepts `{"status":"processing"}` or
  `confirmed`, `processing`, or `cancelled`. Cancelling an order restores its
  stock. A cancelled order cannot be reopened. Shipped, delivered, failed, and
  returned states are set through the delivery API.
