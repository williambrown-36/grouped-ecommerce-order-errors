from __future__ import annotations

import pytest

from ecommerce_errors import CaptureExceptionRequest
from order_workflow import OrderUpdate, OrderWorkflow


class RecordingCapture:
    def __init__(self) -> None:
        self.payloads: list[CaptureExceptionRequest] = []

    def capture(self, payload: CaptureExceptionRequest) -> dict[str, str]:
        self.payloads.append(payload)
        return {"event_id": "event-test"}


def test_receipt_failures_group_by_stage_and_type_not_order() -> None:
    recorder = RecordingCapture()
    workflow = OrderWorkflow(recorder)

    for order_id in ("order-1042", "order-1043"):
        update = OrderUpdate(order_id, "customer-81", "receipt")
        with pytest.raises(ValueError, match="billing address"):
            workflow.run_stage(
                update,
                lambda: (_ for _ in ()).throw(
                    ValueError("receipt template has no billing address")
                ),
            )

    assert len(recorder.payloads) == 2
    assert recorder.payloads[0].fingerprint == [
        "order-workflow",
        "receipt",
        "ValueError",
    ]
    assert recorder.payloads[1].fingerprint == recorder.payloads[0].fingerprint
    assert recorder.payloads[0].context["order_id"] == "order-1042"
    assert recorder.payloads[1].context["order_id"] == "order-1043"
