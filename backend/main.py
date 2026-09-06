from fastapi import FastAPI
from .database import get_connection

app = FastAPI()


@app.get("/")
def home():
    return {"message": "CreamOS API is running"}


@app.get("/test-db")
def test_db():
    connection = get_connection()
    connection.close()

    return {"message": "PostgreSQL connection successful"}


@app.get("/orders")
def get_orders():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            order_id,
            customer_id,
            order_date,
            source,
            payment_method,
            payment_status,
            order_status,
            shipping_cost
        FROM orders
        ORDER BY order_date DESC;
    """)

    orders = cursor.fetchall()

    orders_data = []

    for order in orders:
        orders_data.append({
            "order_id": order[0],
            "customer_id": order[1],
            "order_date": order[2],
            "source": order[3],
            "payment_method": order[4],
            "payment_status": order[5],
            "order_status": order[6],
            "shipping_cost": float(order[7])
        })

    cursor.close()
    connection.close()

    return {"orders": orders_data}