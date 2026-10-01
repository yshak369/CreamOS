from datetime import date
from fastapi import FastAPI
from pydantic import BaseModel
from .database import get_connection

app = FastAPI()

class CustomerCreate(BaseModel):
    name: str
    phone: str
    address: str
    pincode: str

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    unit_cost: float
    discount_amount: float = 0.0

class OrderCreate(BaseModel):
    customer_id: int
    source: str
    payment_method: str
    payment_status: str
    order_status: str
    shipping_cost: float = 50.0
    items: list[OrderItemCreate]

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    payment_method: str
    payment_status: str
    gateway: str | None = None
    transaction_id: str | None = None
    gateway_fee: float = 0.0

@app.post("/customers")
def create_customer(customer: CustomerCreate):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO customers (name, phone, address, pincode)
        VALUES (%s, %s, %s, %s)
        RETURNING customer_id;
    """, (
        customer.name,
        customer.phone,
        customer.address,
        customer.pincode
    ))

    customer_id = cursor.fetchone()[0]

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "message": "Customer created successfully",
        "customer_id": customer_id
    }

@app.post("/payments")
def create_payment(payment: PaymentCreate):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO payments (
                order_id,
                amount,
                payment_method,
                payment_status,
                gateway,
                transaction_id,
                gateway_fee
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING payment_id;
        """, (
            payment.order_id,
            payment.amount,
            payment.payment_method,
            payment.payment_status,
            payment.gateway,
            payment.transaction_id,
            payment.gateway_fee
        ))

        payment_id = cursor.fetchone()[0]
        connection.commit()

        return {
            "message": "Payment recorded successfully",
            "payment_id": payment_id
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

@app.get("/")
def home():
    return {"message": "CreamOS API is running"}


@app.get("/test-db")
def test_db():
    connection = get_connection()
    connection.close()

    return {"message": "PostgreSQL connection successful"}


@app.post("/orders")
def create_order(order: OrderCreate):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # 1. Create the order
        cursor.execute("""
            INSERT INTO orders (
                customer_id,
                source,
                payment_method,
                payment_status,
                order_status,
                shipping_cost
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING order_id;
        """, (
            order.customer_id,
            order.source,
            order.payment_method,
            order.payment_status,
            order.order_status,
            order.shipping_cost
        ))

        order_id = cursor.fetchone()[0]

        # 2. Insert each product into order_items
        for item in order.items:
            cursor.execute("""
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity,
                    unit_price,
                    unit_cost,
                    discount_amount
                )
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                order_id,
                item.product_id,
                item.quantity,
                item.unit_price,
                item.unit_cost,
                item.discount_amount
            ))

        # 3. Save everything together
        connection.commit()

        return {
            "message": "Order created successfully",
            "order_id": order_id,
            "items_added": len(order.items)
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

@app.get("/customers")
def get_customers():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            customer_id,
            name,
            phone,
            address,
            pincode
        FROM customers
        ORDER BY customer_id DESC;
    """)

    customers = cursor.fetchall()

    customers_data = []

    for customer in customers:
        customers_data.append({
            "customer_id": customer[0],
            "name": customer[1],
            "phone": customer[2],
            "address": customer[3],
            "pincode": customer[4]
        })

    cursor.close()
    connection.close()

    return {"customers": customers_data}

@app.get("/products")
def get_products():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            product_id,
            name,
            selling_price,
            cost_price
        FROM products
        ORDER BY product_id DESC;
    """)

    products = cursor.fetchall()

    products_data = []

    for product in products:
        products_data.append({
            "product_id": product[0],
            "name": product[1],
            "selling_price": float(product[2]),
            "cost_price": float(product[3])
        })

    cursor.close()
    connection.close()

    return {"products": products_data}

@app.get("/payments")
def get_payments():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            payment_id,
            order_id,
            amount,
            payment_method,
            payment_status,
            gateway,
            transaction_id,
            gateway_fee
        FROM payments
        ORDER BY payment_id;
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "payment_id": row[0],
            "order_id": row[1],
            "amount": float(row[2]),
            "payment_method": row[3],
            "payment_status": row[4],
            "gateway": row[5],
            "transaction_id": row[6],
            "gateway_fee": float(row[7]) if row[7] is not None else 0
        }
        for row in rows
    ]

@app.get("/expenses")
def get_expenses():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            expense_id,
            expense_date,
            category,
            amount,
            description
        FROM expenses
        ORDER BY expense_date DESC;
    """)

    expenses = cursor.fetchall()

    expenses_data = []

    for expense in expenses:
        expenses_data.append({
            "expense_id": expense[0],
            "expense_date": expense[1],
            "category": expense[2],
            "amount": float(expense[3]),
            "description": expense[4]
        })

    cursor.close()
    connection.close()

    return {"expenses": expenses_data}

@app.get("/analytics/summary")
def get_analytics_summary(
    start_date: date = None,
    end_date: date = None
):    
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM((oi.quantity * oi.unit_price) - oi.discount_amount), 0) AS revenue,
            COALESCE(SUM(oi.quantity * oi.unit_cost), 0) AS product_cost,
            COALESCE(SUM(o.shipping_cost), 0) AS shipping,
            COALESCE(
                (SELECT SUM(amount)
                FROM expenses
                WHERE category = 'Meta Ads'
                AND DATE(expense_date) >= COALESCE(%s, DATE(expense_date))
                AND DATE(expense_date) <= COALESCE(%s, DATE(expense_date))),
                0
            ) AS ads,
            COALESCE(
                (SELECT SUM(p.gateway_fee)
                FROM payments p
                JOIN orders o2
                    ON p.order_id = o2.order_id
                WHERE p.payment_status = 'Paid'
                AND o2.order_status NOT IN ('Cancelled', 'Refunded')
                AND DATE(o2.order_date) >= COALESCE(%s, DATE(o2.order_date))
                AND DATE(o2.order_date) <= COALESCE(%s, DATE(o2.order_date))),
                0
            ) AS payment_fees
        FROM orders o
JOIN order_items oi
    ON o.order_id = oi.order_id
WHERE
    o.order_status NOT IN ('Cancelled', 'Refunded')
    AND DATE(o.order_date) >= COALESCE(%s, DATE(o.order_date))
    AND DATE(o.order_date) <= COALESCE(%s, DATE(o.order_date))
    AND EXISTS (
        SELECT 1
        FROM payments p
        WHERE p.order_id = o.order_id
        AND p.payment_status = 'Paid'
    )
 """, ( 
     start_date,
        end_date,
        start_date,
        end_date,
        start_date,
        end_date))
    result = cursor.fetchone()

    revenue = float(result[0])
    product_cost = float(result[1])
    shipping = float(result[2])
    ads = float(result[3])
    payment_fees = float(result[4])

    net_profit = (
        revenue
        - product_cost
        - shipping
        - ads
        - payment_fees
    )

    cursor.close()
    connection.close()

    return {
        "revenue": revenue,
        "product_cost": product_cost,
        "shipping": shipping,
        "ads": ads,
        "payment_fees": payment_fees,
        "net_profit": net_profit
    }
@app.get("/analytics/orders")
def get_order_metrics():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(DISTINCT o.order_id) AS total_orders,
            COALESCE(
                SUM((oi.quantity * oi.unit_price) - oi.discount_amount)
                / NULLIF(COUNT(DISTINCT o.order_id), 0),
                0
            ) AS average_order_value
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id;
    """)

    result = cursor.fetchone()

    total_orders = result[0]
    average_order_value = float(result[1])

    cursor.close()
    connection.close()

    return {
        "total_orders": total_orders,
        "average_order_value": average_order_value
    }

@app.get("/analytics/channels")
def get_channel_metrics():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            o.source,
            COUNT(DISTINCT o.order_id) AS total_orders,
            COALESCE(
                SUM((oi.quantity * oi.unit_price) - oi.discount_amount),
                0
            ) AS revenue
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        GROUP BY o.source
        ORDER BY revenue DESC;
    """)

    results = cursor.fetchall()

    channels_data = []

    for row in results:
        source = row[0]
        total_orders = row[1]
        revenue = float(row[2])

        average_order_value = (
            revenue / total_orders if total_orders > 0 else 0
        )

        channels_data.append({
            "source": source,
            "total_orders": total_orders,
            "revenue": revenue,
            "average_order_value": average_order_value
        })

    cursor.close()
    connection.close()

    return {"channels": channels_data}

@app.get("/analytics/channel-profit")
def get_channel_profit():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            o.source,
            COUNT(DISTINCT o.order_id) AS total_orders,
            COALESCE(SUM((oi.quantity * oi.unit_price) - oi.discount_amount), 0) AS revenue,
            COALESCE(SUM(oi.quantity * oi.unit_cost), 0) AS product_cost,
            COALESCE(SUM(o.shipping_cost), 0) AS shipping
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        GROUP BY o.source
        ORDER BY revenue DESC;
    """)

    results = cursor.fetchall()

    channels_data = []

    for row in results:
        source = row[0]
        total_orders = row[1]
        revenue = float(row[2])
        product_cost = float(row[3])
        shipping = float(row[4])

        profit_before_ads = revenue - product_cost - shipping

        channels_data.append({
            "source": source,
            "total_orders": total_orders,
            "revenue": revenue,
            "product_cost": product_cost,
            "shipping": shipping,
            "profit_before_ads": profit_before_ads
        })

    cursor.close()
    connection.close()

    return {"channels": channels_data}

@app.get("/analytics/daily")
def get_daily_metrics(start_date: date = None, end_date: date = None):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            DATE(o.order_date) AS date,
            COUNT(DISTINCT o.order_id) AS orders,
            COALESCE(
                SUM((oi.quantity * oi.unit_price) - oi.discount_amount),
                0
            ) AS revenue,
            COALESCE(SUM(oi.quantity * oi.unit_cost), 0) AS product_cost,
            COALESCE(SUM(o.shipping_cost), 0) AS shipping
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        WHERE
            (%s IS NULL OR DATE(o.order_date) >= %s)
            AND
            (%s IS NULL OR DATE(o.order_date) <= %s)
        GROUP BY DATE(o.order_date)
        ORDER BY date DESC;
    """, (start_date, start_date, end_date, end_date))

    results = cursor.fetchall()

    daily_data = []

    for row in results:
        date = row[0]
        orders = row[1]
        revenue = float(row[2])
        product_cost = float(row[3])
        shipping = float(row[4])

        profit_before_ads = revenue - product_cost - shipping

        daily_data.append({
            "date": date,
            "orders": orders,
            "revenue": revenue,
            "product_cost": product_cost,
            "shipping": shipping,
            "profit_before_ads": profit_before_ads
        })

    cursor.close()
    connection.close()

    return {"daily": daily_data}