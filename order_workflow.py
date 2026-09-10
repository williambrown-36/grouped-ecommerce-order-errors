"""Run order stages and group failures at the business boundary."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any, Callable, Protocol, TypeVar

from ecommerce_errors import CaptureExceptionRequest, InfraiErrorClient


Result = TypeVar("Result")


class ErrorCapture(Protocol):
    def capture(self, payload: CaptureExceptionRequest) -> dict[str, Any]: ...


@dataclass(frozen=True)
class OrderUpdate:
    order_id: str
    customer_id: str
    stage: str


class OrderWorkflow:
    """Make stage ownership visible while preserving the original exception."""

    def __init__(self, errors: ErrorCapture) -> None:
        self.errors = errors

    def run_stage(
        self, update: OrderUpdate, operation: Callable[[], Result]
    ) -> Result:
        try:
            return operation()
        except Exception as exc:
            exception_type = type(exc).__name__
            self.errors.capture(
                CaptureExceptionRequest(
                    title=f"{update.stage} failed",
                    message=f"{exception_type}: {exc}",
                    level="error",
                    fingerprint=["order-workflow", update.stage, exception_type],
                    exception=traceback.format_exc(),
                    context={
                        "order_id": update.order_id,
                        "customer_id": update.customer_id,
                        "stage": update.stage,
                    },
                )
            )
            raise


def main() -> None:
    workflow = OrderWorkflow(InfraiErrorClient())
    update = OrderUpdate(
        order_id="order-1042",
        customer_id="customer-81",
        stage="receipt",
    )

    def send_receipt() -> None:
        raise ValueError("receipt template has no billing address")

    try:
        workflow.run_stage(update, send_receipt)
    except ValueError:
        print("Captured receipt error for order-1042; fingerprint: order-workflow/receipt/ValueError")


if __name__ == "__main__":
    main()
