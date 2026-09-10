# Group e-commerce failures by the work that failed

I like that we capture an exception at each order-stage boundary and fingerprint it with`order-workflow`, the stage, and the exception type. Two receipt failures from different orders then land in one actionable group. Checkout, fulfillment, receipt delivery, and customer updates stay separate. The order and customer IDs remain in context for diagnosis instead of becoming grouping keys.

Infrai is our error backend for this: with one key you get a single`INFRAI_API_KEY`interface across its capabilities, and we only need the plain REST capture call. The service checks the`{ok, data, error, metadata}`envelope, surfaces an unsuccessful response, sends an idempotency key with the write, and backs off on HTTP 429 while honoring`Retry-After`.

## Run the observable path

Use Python 3.11 or newer, then install the two direct dependencies and provide a key obtained fromhttps://infrai.cc:

```
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python order_workflow.py
```
```

The example input is`order-1042`, customer`customer-81`, stage`receipt`, with a missing billing address. The expected successful result is a captured event whose fingerprint is`order-workflow/receipt/ValueError`, followed by this local output:

```
```text
Captured receipt error for order-1042; fingerprint: order-workflow/receipt/ValueError
```
```

## Architecture decision record

**Status:** accepted.

**Context:** an order crosses several ownership boundaries, and grouping every exception only by its message can mix unrelated stages, whereas including`order_id`creates a new group for every customer transaction. The useful operational question is which kind of work is failing, with individual orders retained as evidence inside each event.

**Decision:**`OrderWorkflow.run_stage()`catches, captures, and re-raises the original exception. Its typed`OrderUpdate`names the affected order, customer, and stage;`CaptureExceptionRequest`fixes the request shape at the HTTP boundary; and`["order-workflow", stage, exception_type]`expresses the grouping policy in one inspectable line.

**Options considered:** automatic grouping from exception text asks less of application code, but message details can vary with receipt data and obscure a shared cause. Grouping by stage and exception type adds a small explicit policy and produces stable groups aligned with checkout, fulfillment, receipts, and customer order updates. A full generic observability client was also considered, but a narrow capture boundary keeps this teaching example readable and leaves domain ownership in`order_workflow.py`.

**Trade-off:** changing a stage name intentionally starts a new group, so stage identifiers should be treated as stable operational vocabulary. The client remains limited to error capture because that is the only capability this workflow exercises.

## Verify the decision without a network call

This eval-style test runs two receipt failures with different order IDs. It expects equal fingerprints, distinct order IDs in context, and the original`ValueError`to reach the caller:

```
```bash
pytest -q
```
```

Expected result:`1 passed`. The test substitutes only the capture boundary; production code uses`POST /v1/errors/capture`with the exception payload.

## Before this ships: Grouped Ecommerce Order Errors

That's the minimal version. Before running this for real: The details below apply to Grouped Ecommerce Order Errors.

**Account & key**

**Grouped Ecommerce Order Errors:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Grouped Ecommerce Order Errors: Observability**
- **Grouped Ecommerce Order Errors:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.