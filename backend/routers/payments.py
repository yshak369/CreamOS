from fastapi import APIRouter, HTTPException

from ..database import get_cursor
from ..schemas import PaymentCreate, PaymentStatus

router = APIRouter(tags=["payments"])


def insert_payment(cursor, order_id, payment):
    cursor.execute(
        """
        INSERT INTO payments (
            order_id, amount, payment_method, payment_status,
            gateway, transaction_id, gateway_fee
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING payment_id;
        """,
        (
            order_id,
            payment.amount,
            payment.payment_method,
            payment.payment_status.value,
            payment.gateway,
            payment.transaction_id,
            payment.gateway_fee,
        ),
    )
    return cursor.fetchone()["payment_id"]


@router.post("/payments")
def create_payment(payment: PaymentCreate):
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM orders WHERE order_id = %s FOR UPDATE;",
            (payment.order_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail=f"Order {payment.order_id} does not exist.",
            )

        payment_id = insert_payment(cursor, payment.order_id, payment)

        # Keep the order's own payment status in step with its payments
        # (e.g. a COD order becomes Paid once the cash is recorded).
        if payment.payment_status == PaymentStatus.PAID:
            cursor.execute(
                "UPDATE orders SET payment_status = 'Paid' WHERE order_id = %s;",
                (payment.order_id,),
            )

    return {
        "message": "Payment recorded successfully",
        "payment_id": payment_id,
    }


@router.get("/payments")
def get_payments():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                payment_id, order_id, amount, payment_method,
                payment_status, gateway, transaction_id, gateway_fee
            FROM payments
            ORDER BY payment_id;
            """
        )
        rows = cursor.fetchall()

    return [
        {
            **row,
            "amount": float(row["amount"]),
            "gateway_fee": float(row["gateway_fee"] or 0),
        }
        for row in rows
    ]
