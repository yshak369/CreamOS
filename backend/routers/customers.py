from fastapi import APIRouter, Query

from ..database import get_cursor
from ..schemas import CustomerCreate

router = APIRouter(tags=["customers"])


@router.post("/customers")
def create_customer(customer: CustomerCreate):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO customers (name, phone, address, pincode)
            VALUES (%s, %s, %s, %s)
            RETURNING customer_id;
            """,
            (customer.name, customer.phone, customer.address, customer.pincode),
        )
        customer_id = cursor.fetchone()["customer_id"]

    return {
        "message": "Customer created successfully",
        "customer_id": customer_id,
    }


@router.get("/customers")
def get_customers(
    limit: int | None = Query(default=None, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT customer_id, name, phone, address, pincode
            FROM customers
            ORDER BY customer_id DESC
            LIMIT %s OFFSET %s;
            """,
            (limit, offset),
        )
        customers = cursor.fetchall()

    return {"customers": customers}
