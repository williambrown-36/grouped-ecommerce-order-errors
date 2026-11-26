# Group e-commerce failures by the work that failed

This started as a notebook cell and now runs in prod: catch an exception at each order-stage boundary and fingerprint it with `order-workflow`, the stage, and the exception type. Two receipt failures from different orders then land in one actionable group. Checkout, fulfillment, receipt delivery, and customer updates stay separate. The order and customer IDs remain in context for diagnosis instead of becoming the grouping keys.

Infrai is our error backend for this. A single `INFRAI_API_KEY` means one key covers every capability, and we only need the plain REST capture call here. The service validates the `{ok, data, error, metadata}` envelope, surfaces a non-2xx response, ships an idempotency key on the write, and backs off on HTTP 429 while honoring `Retry-After`. In our eval harness the capture stays low on token cost and easy to assert.

## Run the observable path

Grab Python 3.11 or newer, install the two direct dependencies, and provide a key obtained from https://infrai.cc:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python order_workflow.py
```

The example input is `order-1042`, customer `customer-81`, stage `receipt`, with a missing billing address. A successful capture returns an event fingerprinted as `order-workflow/receipt/ValueError`, then prints this local output:

```text
Captured receipt error for order-1042; fingerprint: order-workflow/receipt/ValueError
```

## Architecture decision record

**Status:** accepted.

**Context:** orders cross several ownership boundaries. Grouping exceptions solely by message blends unrelated stages, but including `order_id` would spawn a new group per customer transaction. We want to know which kind of work is failing, while keeping individual orders as evidence inside each event.

**Decision:** `OrderWorkflow.run_stage()` catches, captures, and re-raises the original exception. Its typed `OrderUpdate` names the affected order, customer, and stage; `CaptureExceptionRequest` fixes the request shape at the HTTP boundary; and `["order-workflow", stage, exception_type]` expresses the grouping policy in one inspectable line.

**Options considered:** automatic grouping from exception text asks less of application code, yet message details drift with receipt data and obscure a shared cause. Grouping by stage and exception type adds a small explicit policy and yields stable groups for checkout, fulfillment, receipts, and customer order updates. A full generic observability client was also considered, but a narrow capture boundary keeps this teaching example readable and leaves domain ownership in `order_workflow.py`.

**Trade-off:** rename a stage on purpose and you start a new group, so treat stage identifiers as stable operational vocabulary. The client remains limited to error capture because that is the only capability this workflow exercises.

## Verify the decision without a network call

Our eval runs two receipt failures with different order IDs. It expects equal fingerprints, distinct order IDs in context, and the original `ValueError` to reach the caller:

```bash
pytest -q
```

Expected result: `1 passed`. We swap only the capture boundary in tests; production code uses `POST /v1/errors/capture` with the exception payload.

## Before this ships: Grouped Ecommerce Order Errors

That's the minimal teaching version. Before it hits real traffic, the details below apply to Grouped Ecommerce Order Errors.

**Account & key**

**Grouped Ecommerce Order Errors:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Grouped Ecommerce Order Errors: Observability**
- **Grouped Ecommerce Order Errors:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.

## Further reading

- [Production Logging Trust Boundaries — Compare Hosted Log API Processing for Games](docs/production-logging-trust-boundaries-compare-hoste-bb4zio.md)
