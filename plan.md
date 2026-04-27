# Garment ERP v8.0 — Delivery Plan (Updated)

## Objectives
- ✅ **Completed:** PDF export enhancement program (presets, column selection & order, header/footer/title overrides, orientation, RBAC) across all 17 PDF types.
- ✅ **Completed:** Production Flow Audit remediation (AUDIT-A + AUDIT-B) — data integrity guardrails + workflow completeness + UX polish.
- ✅ **Completed:** Smart Import Feature (Tier 1–3, all data types) — Upload → Map → Preview/Edit → Confirm → Import.
- ✅ **Completed:** Comprehensive E2E validation for delivered features; critical RBAC security bug fixed.
- ✅ **Completed:** Phase 8 enhancement sprint (shipment safety guards, PO edit guardrails, system-wide sorting persistence, Smart Import add-ons, product variants, hook cleanup).
- ✅ **Completed:** Phase 9 critical bug fix sprint (Login JSON error, Smart Import error-path stability, buyer portal authenticated PDF download, missing frontend deps).
- ✅ **Completed (P0):** **Performance tuning — backend pagination** (backward compatible) added to major list endpoints + added missing MongoDB indexes + eliminated worst N+1 patterns.
- ✅ **Verified (iteration_13, 100% pass):** Production Flow Audit fixes re-tested in continuation session — all 9 bugs (C-1, C-2, C-3, H-1, H-2, H-3, H-4, M-1, M-3) confirmed fixed and **fully compatible with the OVERPRODUCTION/UNDERPRODUCTION variance feature**. Cap logic uses `produced_qty` (not `ordered_qty`), so variance flow is preserved end-to-end.
- ✅ **Completed (Phase 10C):** Frontend server-side pagination rolled out across 5 modules — Products, Invoice, ProductionPO (DataTable serverPagination mode), Activity Logs & Payments (custom UI + PaginationFooter). Backward-compatible: legacy DataTable usage unaffected.
- ✅ **Completed (Phase 10B-rem):** Batched N+1 in `/api/reports/{production|shipment|progress|return|accessory}`, `/api/production-monitoring-v2`, `/api/distribusi-kerja`. Fixed an orphan-syntax block at end of `server.py` left from a prior merge.
- ✅ **Verified (iteration_14, 100% backend pass):** Pagination envelopes correct on all migrated endpoints, legacy mode preserved, audit fixes still pass after refactor.
- 🎯 **Current Focus (next):** Performance tuning follow-up — **frontend server-side pagination** rollout (DataTable + non-DataTable screens) + complete remaining backend N+1 reductions on report endpoints.

---

## Implementation Steps

### Phase 1 — Core Flow POC (Isolation): Prove preset → PDF rendering works reliably
**Status: ✅ COMPLETED**

**What we verified**
1. All PDF export endpoints work with seeded data; buyer shipment summary + per-dispatch both export correctly.
2. PDF Config CRUD works (create/read/update/delete/set default).
3. Column filtering via `config_id` and default preset auto-apply both work.
4. Confirmed critical branding bug: Company Settings fields were saved but not rendered.
5. Confirmed validation gap: unknown `pdf_type` accepted by preset creation.

**Confirmed bugs from Phase 1**
- **CRITICAL:** Company Settings branding fields were not rendered in PDFs.
- **LOW:** `POST /api/pdf-export-configs` accepted unknown `pdf_type`.

---

### Phase 2 — Bug Fixes: Company branding + validation hardening
**Status: ✅ COMPLETED**

**User stories delivered**
1. Company Settings branding is always reflected in exported PDFs.
2. System rejects invalid presets (unknown `pdf_type`).
3. PDF generation remains stable even if logo URL is invalid/unreachable.

---

### Phase 3 — Enhancements: Full preset power (columns/order/header-footer/orientation) + RBAC
**Status: ✅ COMPLETED (Backend + Frontend)**

**User stories delivered**
1. Admin can configure presets for all 17 PDF types.
2. Admin can drag & drop columns to set ordering.
3. Admin can select additional DB-backed columns beyond the original minimal set.
4. Admin can override title/header/footer per preset with a clear precedence model.
5. Admin can set page orientation per preset (auto/portrait/landscape).
6. Non-admin users can view presets and export PDFs but cannot modify presets (RBAC).

---

### Phase 4 — End-to-End Testing & Validation (PDF Export)
**Status: ✅ COMPLETED (per `test_reports/iteration_6.json`)**

---

### Phase 5 — Productionization (optional)
**Status: ⏳ OPTIONAL / FUTURE**

---

## Phase AUDIT-A — Production Flow Data-Integrity Guardrails
**Status: ✅ COMPLETED (2026-04-24)**

---

## Phase AUDIT-B — Workflow Completeness & UX Polish
**Status: ✅ COMPLETED (2026-04-24)**

---

## Phase 6 — Smart Import Feature (All tiers + all data types)
**Status: ✅ COMPLETED (implementation) (2026-04-24)**

---

## Phase 7 — End-to-End Testing & Validation (All recent features)
**Status: ✅ COMPLETED (2026-04-24)**

---

## Phase 8 — Multi-Issue Enhancement Sprint (Execution Approved)
**Status: ✅ COMPLETED (Implementation + Verification)**

---

## Phase 9 — Critical Bug Fixes (Login / Smart Import / PDF Export)
**Status: ✅ COMPLETED (2026-04-27)**

### Context
User reported three bugs:
1. Login bug — `Failed to execute 'json' on 'Response': body stream already read`
2. Smart Import bug (same root cause on error responses)
3. Suspected PDF export bug

### Root Cause
Emergent preview logger wraps `window.fetch` and calls `response.text()` on non-OK responses without cloning, consuming the body stream and breaking later `res.json()` calls.

### Fixes Delivered
1. `frontend/public/index.html` — preserve native fetch and install clone-safe wrapper.
2. `frontend/src/components/erp/Login.jsx` — use `detail` and defensive JSON parsing.
3. `frontend/src/components/erp/BuyerPortalApp.jsx` — authenticated PDF download via fetch+blob.
4. Installed missing deps: `xlsx`, `jspdf`, `jspdf-autotable`.

### Verification
- Login wrong creds shows proper message.
- Smart Import completes end-to-end.
- PDF exports verified (production-po + reports) and content validated via text extraction.

---

## Phase 10 — Performance Tuning (P0-first)
**Status: ✅ Phase 10A COMPLETED (2026-04-27); Phase 10B PARTIAL; Phase 10C IN PROGRESS (planned)**

### Context / Problem
Current UI uses **client-side pagination** (`DataTable.jsx` slices arrays), but backend previously returned full datasets for many list endpoints (frequent `.to_list(None)`), which will not scale. Several endpoints also contained **N+1 query patterns** that multiplied DB calls per request.

### High-level Strategy
- **10A (P0)**: Add **backend pagination** first with **backward compatibility** so frontend remains functional during rollout.
- **10B (P0/P1)**: Reduce worst N+1 patterns via batch fetches or aggregation.
- **10C (P1/P2)**: Update frontend tables to true server-side pagination and caching.

---

### Phase 10A — Backend Pagination (Backward-Compat) + Missing Indexes
**Status: ✅ COMPLETED (2026-04-27)**

#### Goals (P0)
1. Stop endpoints from loading unbounded data by default (or provide safe paging when requested).
2. Preserve current frontend behavior during rollout.
3. Ensure queries are index-backed on common filters.

#### Backward-compat policy (implemented)
- If request includes **`page`** (and optionally `per_page`), endpoint returns:
  ```json
  {"items": [...], "total": 123, "page": 1, "per_page": 20, "total_pages": 7}
  ```
- If request does **not** include `page`, endpoint returns the **legacy array response**.
- Safety caps and limits:
  - `per_page` default: 20
  - `per_page` max: 200
  - Legacy (no page/per_page) query safety cap: 1000 docs

#### API conventions (standardized)
- Query params:
  - `page` (1-based), `per_page` (default 20, max 200)
  - `sort_by` (default `created_at`), `sort_dir` (`asc|desc`)
  - `search`/filters remain per endpoint

#### Implemented endpoints (completed)
Pagination + sorting support added (with legacy-array compatibility) for:
- `/api/production-pos` (**also includes batch-fetch N+1 fix**) 
- `/api/vendor-shipments` (**batch-fetch N+1 fix**) 
- `/api/buyer-shipments` (**batch-fetch N+1 fix**) 
- `/api/invoices`
- `/api/payments`
- `/api/invoice-edit-requests`
- `/api/products`
- `/api/garments`
- `/api/product-variants`
- `/api/buyers` (now supports both new envelope and legacy `?paginated=true` callers)
- `/api/users`
- `/api/activity-logs` (keeps legacy `?limit=` behaviour; adds page/per_page envelope)
- `/api/material-requests`
- `/api/production-returns` (**batch-fetch N+1 fix**) 
- `/api/production-jobs` (**batch-fetch N+1 fix**) 
- `/api/work-orders`
- `/api/accounts-payable`
- `/api/accounts-receivable`
- `/api/material-defect-reports`

#### Missing indexes added (fast win)
Added startup index creation for common query fields:
- `po_accessories.po_id`
- `production_return_items.return_id`
- `production_return_items.po_item_id`
- `invoice_adjustments.invoice_id`
- `po_items.serial_number`
- `work_orders.po_id`
- `production_progress.work_order_id`
- `material_requests.request_type`, `material_requests.status`
- `payments.invoice_id`
- `production_pos.status`, `production_pos.vendor_id`, plus `production_pos.created_at(-1)`
- `invoices.status`, `invoices.created_at(-1)`
- `payments.created_at(-1)`
- `production_returns.status`, `production_returns.created_at(-1)`
- `buyer_shipments.created_at(-1)`
- `vendor_shipments.created_at(-1)`
- `work_orders.created_at(-1)`
- `production_jobs.created_at(-1)`

#### Implementation notes (what changed)
- Removed `.to_list(None)` on the above list endpoints.
- Added standardized pagination helpers to backend.
- Introduced batched reads + aggregation for totals where needed to reduce DB round-trips.

#### Verification
- Manual curl verification:
  - Legacy calls (no `page/per_page`) return arrays.
  - `?page=1&per_page=5` returns envelopes with correct keys.
  - `per_page` capped at 200.
  - Sorting and search filters work.
- UI smoke check: Dashboard and Production PO screens load correctly.
- Automated backend tests: `test_reports/iteration_12.json` indicates **53/55 passed**, no critical bugs.
  - Noted non-critical observations: `/api/buyers?paginated=true` now returns the new envelope format.

#### Exit criteria
✅ Completed.

---

### Phase 10B — N+1 Query Reduction (Heaviest list endpoints)
**Status: 🟡 PARTIALLY COMPLETED (2026-04-27)**

#### What was completed inline during 10A
The heaviest endpoints were optimized to eliminate the worst N+1 patterns:
- `GET /api/production-pos`: batch fetch `po_items`, `po_accessories`, aggregated vendor/buyer shipped totals per `po_item_id`.
- `GET /api/vendor-shipments`: batch fetch `vendor_shipment_items`, aggregate child shipment counts and accessory counts.
- `GET /api/buyer-shipments`: batch fetch `buyer_shipment_items`.
- `GET /api/production-returns`: batch fetch `production_return_items`.
- `GET /api/production-jobs`: batch fetch child jobs + job_items + aggregate shipped totals by job_item_id.

#### Remaining scope (10B-rem — planned)
Focus: **report endpoints** and other endpoints that still use looped `.find_one()`/`.find()` patterns.

**10B-rem tasks**
1. **Inventory remaining N+1 hotspots**
   - Search backend for patterns like `for ...: await db.*.find_one()` and `.to_list(None)` inside loops.
   - Prioritize endpoints with large fan-out (reports dashboards).
2. **Batch strategy**
   - Replace per-row lookups with:
     - `$in` queries + in-memory maps, or
     - aggregation pipelines (`$group`) for totals, or
     - selective `$lookup` for stable join paths.
3. **Protect backward compatibility**
   - Keep response shapes stable unless adding *new* fields.
4. **Verification**
   - Use before/after request tracing (counts of DB calls) + payload time comparison.
   - Add/extend targeted regression tests around the optimized report endpoints.

**Exit criteria (10B-rem)**
- No report endpoint performs per-row DB queries for common list sizes.
- Latency improved measurably (at least fewer DB round-trips; ideally lower p95).

---

### Phase 10C — Frontend tuning: True server-side pagination rollout
**Status: 🟠 IN PROGRESS (implementation planned next)**

#### Problem remaining
Even with backend pagination implemented, current screens still download full lists because:
- `DataTable.jsx` paginates client-side (slicing arrays)
- Modules call list endpoints without `page/per_page`

#### Strategy (Phase 10C — approved)
**Backwards-compatible** frontend change:
1. Enhance `DataTable.jsx` with an **optional server-side pagination mode** via a new prop (proposed name):
   - `serverPagination` (object) containing:
     - `enabled: true`
     - `fetcher(params)` that calls the backend with `page/per_page/sort_by/sort_dir/search` and returns the envelope
     - `initialPage`, `initialPerPage`, `initialSort` (optional)
     - `externalDeps` (optional) so filters trigger a refetch
   - When `serverPagination` is **absent**, DataTable behaves exactly as today (client-side search/sort/paging).
2. Introduce a shared `PaginationFooter` component for screens that **do not** use DataTable (custom lists/tables), but still need consistent paging UX.

#### Module migration scope (requested)
**A) DataTable-based screens (migrate to serverPagination mode)**
1. `ProductsModule.jsx` → `GET /api/products?page=...&per_page=...&search=...&sort_by=...&sort_dir=...`
2. `ProductionPOModule.jsx` → `GET /api/production-pos?page=...` plus existing filters (`search`, `status`) and sorting
3. `InvoiceModule.jsx` → `GET /api/invoices?page=...` plus `status` filter and sorting

**B) Non-DataTable screens (use PaginationFooter + server paging in-module)**
4. `PaymentModule.jsx` (custom tabbed table)
   - Paginate `GET /api/payments` for **each tab** (vendor/customer)
   - Avoid downloading all invoices if possible (follow-up: add a paginated unpaid invoice picker endpoint or filter)
5. `ActivityLogModule.jsx` (custom list)
   - Switch from `limit=200` to `page/per_page`
   - Keep filters (`module`, `user_id`) in query params

#### Implementation steps (10C)
1. **Create** `PaginationFooter.jsx` (shared): shows range, total, prev/next, numbered pages; supports `per_page` selector.
2. **Refactor** `DataTable.jsx`:
   - Add serverPagination mode (loading state, refetch on page/sort/search changes)
   - In server mode, sorting should translate to `sort_by/sort_dir` and request fresh data
   - Search should debounce (e.g. 250–400ms) to avoid hammering the backend
3. **Migrate** modules in order:
   1) Products (simplest)
   2) Invoices
   3) Production PO (largest payload + extra filters)
   4) Activity Logs
   5) Payments
4. **QA & verification**
   - Confirm network payload is reduced (20–50 rows per request)
   - Confirm filters reset page to 1
   - Confirm sort persistence remains correct (storageKey still used)

#### Exit criteria (10C)
- Key list screens load only 20–50 rows at a time from the backend.
- Filter/sort triggers re-fetch (and resets to page 1).
- Noticeable improvement in network payload + time-to-interactive for large datasets.
- Legacy behavior preserved for screens not yet migrated.

---

## Next Actions (Immediate)
1. Implement **Phase 10C**:
   - Add `serverPagination` mode to `DataTable.jsx`
   - Add `PaginationFooter` for non-DataTable UIs
   - Migrate: Products, ProductionPO, Invoice, ActivityLog, Payment
2. Implement **Phase 10B-rem**:
   - Identify remaining N+1 patterns on report endpoints and batch-fix
3. Run verification:
   - Frontend smoke tests for all migrated screens
   - (Optional) targeted backend perf checks for optimized report endpoints

## Success Criteria
- ✅ P0: Backend supports safe pagination and avoids unbounded reads.
- ✅ P0: Heaviest list endpoints no longer have catastrophic N+1 query behaviour.
- 🎯 Next: Frontend stops downloading full datasets and uses true server paging.
- 🎯 Next: Remaining report endpoints avoid per-row DB reads and scale with dataset size.
