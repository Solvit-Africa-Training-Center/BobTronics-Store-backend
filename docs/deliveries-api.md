# Deliveries API

All routes are under `/api/v1/deliveries/`.

## Customer tracking

Authenticated customers can use:

- `GET /deliveries/` to list their own deliveries.
- `GET /deliveries/{delivery_id}/` to retrieve one of their deliveries.

The response includes the related order ID and status, delivery address and
method, tracking number, delivery status, shipping fee, and shipment timestamps.

## Admin fulfillment

Admins and super-admins can use:

- `GET /deliveries/admin/` to list deliveries. Optional filters: `status`,
  `delivery_method`, and `order`.
- `GET /deliveries/admin/{delivery_id}/` to retrieve a delivery.
- `PATCH /deliveries/admin/{delivery_id}/` to update delivery address/method,
  tracking number, shipping fee, or status.

Allowed status transitions are pending to in transit, failed, or returned;
in transit to out for delivery, delivered, failed, or returned; out for
delivery to delivered, failed, or returned; and failed to in transit or
returned. Delivered and returned are terminal. Moving to in transit or
delivered sets the corresponding timestamp and updates the order status.
Failed and returned deliveries also set the order status to `failed` and
`returned`; a failed delivery that resumes transit sets the order back to
`shipped`.
