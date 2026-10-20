# Promotions API

All paths start with `/api/v1/promotions/`.

- `GET /promotions/` lists product discounts that are active today. Optional
  filter: `product`.
- Admins and super-admins can manage product discounts through
  `/promotions/admin/discounts/` using standard list, create, retrieve, update,
  and delete methods. List filters: `product`, `discount_type`, `is_active`.
- Admins and super-admins can manage promo codes through
  `/promotions/admin/codes/` using standard list, create, retrieve, update, and
  delete methods. List filters: `discount_type`, `is_active`.

Percentage discounts cannot exceed 100%. Promo codes are normalized to
uppercase. Promo code usage counts are read-only and are incremented by
successful order creation.
