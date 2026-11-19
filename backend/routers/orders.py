from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query

from ..database import get_cursor
from ..schemas import OrderCreate, PaymentStatus
from .payments import insert_payment

router = APIRouter(tags=["orders"])

CENT = Decimal("0.01")


@router.post("/orders")
def create_order(order: OrderCreate):
    # A paid order must come with its payment record.
    if order.payment is None and order.payment_status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=400,
            detail="A payment record is required for paid orders.",
        )

    with get_cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM customers WHERE customer_id = %s;",
            (order.customer_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=400,
                detail=f"Customer {order.customer_id} does not exist.",
            )

        # Look up products so missing prices can default to the catalogue.
        product_ids = sorted({item.product_id for item in order.items})
        cursor.execute(
            """
            SELECT product_id, selling_price, cost_price
            FROM products
            WHERE product_id = ANY(%s);
            """,
            (product_ids,),
        )
        catalogue = {row["product_id"]: row for row in cursor.fetchall()}

        missing = [pid for pid in product_ids if pid not in catalogue]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown product id(s): {missing}",
            )

        lines = []
        for item in order.items:
            product = catalogue[item.product_id]
            unit_price = (
                item.unit_price
                if item.unit_price is not None
                else product["selling_price"]
            )
            unit_cost = (
                item.unit_cost
                if item.unit_cost is not None
                else product["cost_price"]
            )
            line_total = item.quantity * unit_price
            if item.discount_amount > line_total:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Discount for product {item.product_id} is larger "
                        "than the line total."
                    ),
                )
            lines.append((item, unit_price, unit_cost, line_total))

        expected_amount = sum(
            (line_total - item.discount_amount
             for item, _, _, line_total in lines),
            Decimal("0"),
        ).quantize(CENT)

        if (
            order.payment is not None
            and order.payment.payment_status == PaymentStatus.PAID
            and order.payment.amount.quantize(CENT) != expected_amount
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Incorrect payment amount. Expected ₹{expected_amount:.2f}",
            )

        order_payment_status = (
            order.payment.payment_status
            if order.payment is not None
            else order.payment_status
        )

        cursor.execute(
            """
            INSERT INTO orders (
                customer_id, source, payment_method,
                payment_status, order_status, shipping_cost
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING order_id;
            """,
            (
                order.customer_id,
                order.source,
                order.payment_method,
                order_payment_status.value,
                order.order_status.value,
                order.shipping_cost,
            ),
        )
        order_id = cursor.fetchone()["order_id"]

        for item, unit_price, unit_cost, _ in lines:
            cursor.execute(
                """
                INSERT INTO order_items (
                    order_id, product_id, quantity,
                    unit_price, unit_cost, discount_amount
                )
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (
                    order_id,
                    item.product_id,
                    item.quantity,
                    unit_price,
                    unit_cost,
                    item.discount_amount,
                ),
            )

        payment_id = None
        if order.payment is not None:
            payment_id = insert_payment(cursor, order_id, order.payment)

    return {
        "message": "Order created successfully",
        "order_id": order_id,
        "items_added": len(order.items),
        "order_total": float(expected_amount),
        "payment_id": payment_id,
    }


@router.get("/orders")
def get_orders(
    limit: int | None = Query(default=None, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                o.order_id,
                o.order_date,
                o.customer_id,
                c.name AS customer,
                o.source,
                o.payment_method,
                o.payment_status,
                o.order_status,
                o.shipping_cost,
                COALESCE(SUM(oi.quantity), 0) AS units,
                COALESCE(
                    SUM(oi.quantity * oi.unit_price - oi.discount_amount), 0
                ) AS order_total
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            LEFT JOIN order_items oi ON oi.order_id = o.order_id
            GROUP BY o.order_id, c.name
            ORDER BY o.order_id DESC
            LIMIT %s OFFSET %s;
            """,
            (limit, offset),
        )
        rows = cursor.fetchall()

    return {
        "orders": [
            {
                **row,
                "shipping_cost": float(row["shipping_cost"] or 0),
                "units": int(row["units"]),
                "order_total": float(row["order_total"]),
            }
            for row in rows
        ]
    }
