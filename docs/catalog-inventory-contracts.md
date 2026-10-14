# Catalog and inventory service contracts

This note records the service interfaces for catalog work and the agreed
StockMovement extension. Checkout integration remains a shared contract with
the orders owner; it should call these services rather than update stock or
calculate discounts independently.

## Low-stock reporting

`low_stock_products(threshold)` returns products with
`stock_quantity <= threshold`, ordered by stock then name. The threshold must
be a non-negative integer. Hidden or unavailable products are included because
they still represent inventory to manage.

Admins can query `GET /api/v1/catalog/admin/products/low-stock/?threshold=N`.
The threshold is required; there is no implicit low-stock cutoff or product
schema field.

## Stock service

- `check_stock(items, require_available=True)` validates requested
  `(product_id, quantity)` pairs without changing inventory. Its result can
  become stale, so it is informational.
- `deduct_stock(items, require_available=True, source="other", reason="",
  actor=None, reference_id="", movement_type=...)` atomically deducts all
  requested quantities, creates a StockMovement per product, and returns
  `{product_id: stock_left}`. It fails as a unit if any line cannot be fulfilled.
- `restore_stock(items, source="other", reason="", actor=None,
  reference_id="", movement_type=...)` atomically restores quantities,
  records each movement, and returns `{product_id: stock_now}`.

Orders should use `deduct_stock` as part of order creation and `restore_stock`
when a qualifying cancellation/refund returns units. Use a stable source value,
the acting user when available, and the order ID as `reference_id`.

## Discount calculation

`calculate_discount(product, on_date=None)` returns the best active discount
amount for one unit, rounded to cents and capped at the product price.
`calculate_discounted_price(product, on_date=None)` returns the resulting unit
price. Discounts do not stack. When checkout integrates this service, it should
persist the product's original unit price, the per-unit savings multiplied by
quantity in `discount_amount`, and the discounted line total in `subtotal`;
confirm those field semantics with the orders owner before integration.

## ERD addendum: StockMovement

The team approved persistent stock-movement records as an extension to the
original ERD. The `stock_movements` table contains:

| Field | Meaning |
| --- | --- |
| `movement_id` (PK) | Movement identifier |
| `product_id` (FK) | Product whose stock changed; product deletion is protected |
| `actor_id` (nullable FK) | User responsible, if known |
| `movement_type` | Deduction, restoration, or adjustment |
| `source` | Origin such as checkout, cancellation, or inventory adjustment |
| `quantity_change` | Signed units changed; never zero |
| `quantity_before` | Stock before the movement |
| `quantity_after` | Stock after the movement |
| `reason` | Optional explanation |
| `reference_id` | Optional related record identifier, such as an order ID |
| `created_at` | Creation timestamp |

Relationships: one Product has many StockMovement records; each movement
belongs to one Product. A User can be associated with many movements, while a
movement may have no actor when the source is automated or unknown.
