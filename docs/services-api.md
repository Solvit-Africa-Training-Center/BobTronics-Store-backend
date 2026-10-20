# Service requests API

All routes start with `/api/v1/services/`. Customer routes require an
authenticated customer; admin routes require an admin or super-admin.

- `POST /services/` submits a request with `name`, `description`, and a
  `service_type` choice (`hardware_maintenance`,
  `software_troubleshooting`, `network_infrastructure`, `it_consultancy`,
  `project_management`, or `other`). New requests start with status `new`.
- `GET /services/` lists the current customer's requests.
- `GET /services/{service_id}/` retrieves one of that customer's requests.
- `POST /services/{service_id}/cancel/` cancels a request while it is still
  `new`.
- `GET /services/admin/` lists all requests. Optional filters: `status`,
  `service_type`, and `user`.
- `GET /services/admin/{service_id}/` retrieves a request with customer email.
- `PATCH /services/admin/{service_id}/` updates `status`, `estimated_cost`, or
  `final_cost`. Status transitions are `new` to `in_progress` or `cancelled`,
  and `in_progress` to `completed` or `cancelled`. Completed and cancelled
  requests are terminal. Completing a request records `completed_at`.
