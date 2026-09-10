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
def get_analytics_summary():
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
                 WHERE category = 'Meta Ads'),
                0
            ) AS ads
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id;
    """)

    result = cursor.fetchone()

    revenue = float(result[0])
    product_cost = float(result[1])
    shipping = float(result[2])
    ads = float(result[3])

    net_profit = revenue - product_cost - shipping - ads

    cursor.close()
    connection.close()

    return {
        "revenue": revenue,
        "product_cost": product_cost,
        "shipping": shipping,
        "ads": ads,
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