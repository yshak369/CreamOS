from datetime import date
from fastapi import FastAPI
from pydantic import BaseModel
from .database import get_connection
from fastapi import FastAPI, HTTPException

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

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    payment_method: str
    payment_status: str
    gateway: str | None = None
    transaction_id: str | None = None
    gateway_fee: float = 0.0


class OrderPaymentCreate(BaseModel):
    amount: float
    payment_method: str
    payment_status: str
    gateway: str | None = None
    transaction_id: str | None = None
    gateway_fee: float = 0.0


class OrderCreate(BaseModel):
    customer_id: int
    source: str
    payment_method: str
    payment_status: str
    order_status: str
    shipping_cost: float = 50.0
    items: list[OrderItemCreate]
    payment: OrderPaymentCreate | None = None



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
        # 1. Calculate expected order total
        expected_amount = round(
            sum(
                item.quantity * item.unit_price - item.discount_amount
                for item in order.items
            ),
            2
        )

        # 2. Validate paid payment amount
        if (
            order.payment is not None
            and order.payment.payment_status == "Paid"
            and round(order.payment.amount, 2) != expected_amount
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Incorrect payment amount. Expected ₹{expected_amount:.2f}"
            )

        # Prevent paid orders without a payment record
        if (
            order.payment is None
            and order.payment_status == "Paid"
        ):
            raise HTTPException(
                status_code=400,
                detail="A payment record is required for paid orders."
            )

        # 3. Determine payment status
        if order.payment is not None:
            order_payment_status = order.payment.payment_status
        else:
            order_payment_status = order.payment_status

        # 4. Create the order
        cursor.execute("""
            INSERT INTO orders (
                customer_id, source, payment_method,
                payment_status, order_status, shipping_cost
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING order_id;
        """, (
            order.customer_id,
            order.source,
            order.payment_method,
            order_payment_status,
            order.order_status,
            order.shipping_cost
        ))

        order_id = cursor.fetchone()[0]

        # 5. Add products
        for item in order.items:
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, product_id, quantity,
                    unit_price, unit_cost, discount_amount
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

        # 6. Add payment if supplied
        payment_id = None

        if order.payment is not None:
            payment = order.payment

            cursor.execute("""
                INSERT INTO payments (
                    order_id, amount, payment_method,
                    payment_status, gateway, transaction_id,
                    gateway_fee
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING payment_id;
            """, (
                order_id,
                payment.amount,
                payment.payment_method,
                payment.payment_status,
                payment.gateway,
                payment.transaction_id,
                payment.gateway_fee
            ))

            payment_id = cursor.fetchone()[0]

        # 7. Commit all changes
        connection.commit()

        return {
            "message": "Order created successfully",
            "order_id": order_id,
            "items_added": len(order.items),
            "payment_id": payment_id
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



@app.get("/analytics/monthly")
def get_monthly_analytics(
    start_date: date = None,
    end_date: date = None
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            WITH valid_orders AS (
                SELECT
                    o.order_id,
                    o.order_date,
                    o.shipping_cost
                FROM orders o
                WHERE o.order_status NOT IN ('Cancelled', 'Refunded')
                  AND (%s IS NULL OR DATE(o.order_date) >= %s)
                  AND (%s IS NULL OR DATE(o.order_date) <= %s)
                  AND EXISTS (
                      SELECT 1
                      FROM payments p
                      WHERE p.order_id = o.order_id
                        AND p.payment_status = 'Paid'
                  )
            ),
            order_totals AS (
                SELECT
                    vo.order_id,
                    vo.order_date,
                    vo.shipping_cost,
                    COALESCE(
                        SUM(
                            (oi.quantity * oi.unit_price)
                            - oi.discount_amount
                        ), 0
                    ) AS revenue,
                    COALESCE(
                        SUM(oi.quantity * oi.unit_cost), 0
                    ) AS product_cost
                FROM valid_orders vo
                JOIN order_items oi ON oi.order_id = vo.order_id
                GROUP BY
                    vo.order_id,
                    vo.order_date,
                    vo.shipping_cost
            ),
            monthly_orders AS (
                SELECT
                    DATE_TRUNC('month', order_date)::date AS month,
                    COUNT(DISTINCT order_id) AS orders,
                    SUM(revenue) AS revenue,
                    SUM(product_cost) AS product_cost,
                    SUM(shipping_cost) AS shipping
                FROM order_totals
                GROUP BY DATE_TRUNC('month', order_date)::date
            ),
            monthly_ads AS (
                SELECT
                    DATE_TRUNC('month', expense_date)::date AS month,
                    SUM(amount) AS ads
                FROM expenses
                WHERE category = 'Meta Ads'
                  AND (%s IS NULL OR DATE(expense_date) >= %s)
                  AND (%s IS NULL OR DATE(expense_date) <= %s)
                GROUP BY DATE_TRUNC('month', expense_date)::date
            ),
            monthly_fees AS (
                SELECT
                    DATE_TRUNC('month', vo.order_date)::date AS month,
                    SUM(p.gateway_fee) AS payment_fees
                FROM valid_orders vo
                JOIN payments p ON p.order_id = vo.order_id
                WHERE p.payment_status = 'Paid'
                GROUP BY DATE_TRUNC('month', vo.order_date)::date
            ),
            report_months AS (
                SELECT month FROM monthly_orders
                UNION
                SELECT month FROM monthly_ads
            )
            SELECT
                rm.month,
                COALESCE(mo.orders, 0),
                COALESCE(mo.revenue, 0),
                COALESCE(mo.product_cost, 0),
                COALESCE(mo.shipping, 0),
                COALESCE(ma.ads, 0),
                COALESCE(mf.payment_fees, 0)
            FROM report_months rm
            LEFT JOIN monthly_orders mo ON mo.month = rm.month
            LEFT JOIN monthly_ads ma ON ma.month = rm.month
            LEFT JOIN monthly_fees mf ON mf.month = rm.month
            ORDER BY rm.month DESC;
        """, (
            start_date, start_date,
            end_date, end_date,
            start_date, start_date,
            end_date, end_date
        ))

        results = cursor.fetchall()
        monthly_data = []

        for row in results:
            month = row[0]
            orders = row[1]
            revenue = float(row[2])
            product_cost = float(row[3])
            shipping = float(row[4])
            ads = float(row[5])
            payment_fees = float(row[6])

            net_profit = (
                revenue
                - product_cost
                - shipping
                - ads
                - payment_fees
            )

            monthly_data.append({
                "month": month.strftime("%Y-%m"),
                "orders": orders,
                "revenue": revenue,
                "product_cost": product_cost,
                "shipping": shipping,
                "ads": ads,
                "payment_fees": payment_fees,
                "net_profit": net_profit
            })

        return {"monthly": monthly_data}

    finally:
        cursor.close()
        connection.close()


@app.get("/analytics/channels")
def get_channel_metrics():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            WITH valid_orders AS (
                SELECT o.order_id, o.source
                FROM orders o
                WHERE o.order_status NOT IN ('Cancelled', 'Refunded')
                  AND EXISTS (
                      SELECT 1
                      FROM payments p
                      WHERE p.order_id = o.order_id
                        AND p.payment_status = 'Paid'
                  )
            ),
            order_totals AS (
                SELECT
                    vo.order_id,
                    vo.source,
                    SUM(
                        (oi.quantity * oi.unit_price)
                        - oi.discount_amount
                    ) AS revenue
                FROM valid_orders vo
                JOIN order_items oi
                    ON oi.order_id = vo.order_id
                GROUP BY vo.order_id, vo.source
            )
            SELECT
                source,
                COUNT(*) AS total_orders,
                COALESCE(SUM(revenue), 0) AS revenue,
                COALESCE(AVG(revenue), 0) AS average_order_value
            FROM order_totals
            GROUP BY source
            ORDER BY revenue DESC;
        """)

        results = cursor.fetchall()

        channels_data = []

        for row in results:
            channels_data.append({
                "source": row[0],
                "total_orders": row[1],
                "revenue": float(row[2]),
                "average_order_value": round(float(row[3]), 2)
            })

        return {"channels": channels_data}

    finally:
        cursor.close()
        connection.close()



@app.get("/analytics/channel-profit")
def get_channel_profit():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            WITH valid_orders AS (
                SELECT
                    o.order_id,
                    o.source,
                    o.shipping_cost
                FROM orders o
                WHERE o.order_status NOT IN ('Cancelled', 'Refunded')
                  AND EXISTS (
                      SELECT 1
                      FROM payments p
                      WHERE p.order_id = o.order_id
                        AND p.payment_status = 'Paid'
                  )
            ),
            order_totals AS (
                SELECT
                    vo.order_id,
                    vo.source,
                    vo.shipping_cost,
                    SUM(
                        (oi.quantity * oi.unit_price)
                        - oi.discount_amount
                    ) AS revenue,
                    SUM(oi.quantity * oi.unit_cost) AS product_cost
                FROM valid_orders vo
                JOIN order_items oi
                    ON oi.order_id = vo.order_id
                GROUP BY
                    vo.order_id,
                    vo.source,
                    vo.shipping_cost
            )
            SELECT
                source,
                COUNT(*) AS total_orders,
                COALESCE(SUM(revenue), 0) AS revenue,
                COALESCE(SUM(product_cost), 0) AS product_cost,
                COALESCE(SUM(shipping_cost), 0) AS shipping
            FROM order_totals
            GROUP BY source
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

        return {"channels": channels_data}

    finally:
        cursor.close()
        connection.close()




@app.get("/analytics/daily")
def get_daily_metrics(start_date: date = None, end_date: date = None):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            WITH valid_orders AS (
                SELECT
                    o.order_id,
                    o.order_date,
                    o.shipping_cost
                FROM orders o
                WHERE o.order_status NOT IN ('Cancelled', 'Refunded')
                  AND (%s IS NULL OR DATE(o.order_date) >= %s)
                  AND (%s IS NULL OR DATE(o.order_date) <= %s)
                  AND EXISTS (
                      SELECT 1
                      FROM payments p
                      WHERE p.order_id = o.order_id
                        AND p.payment_status = 'Paid'
                  )
            ),
            order_totals AS (
                SELECT
                    vo.order_id,
                    DATE(vo.order_date) AS date,
                    vo.shipping_cost,
                    SUM(
                        (oi.quantity * oi.unit_price)
                        - oi.discount_amount
                    ) AS revenue,
                    SUM(oi.quantity * oi.unit_cost) AS product_cost
                FROM valid_orders vo
                JOIN order_items oi
                    ON oi.order_id = vo.order_id
                GROUP BY
                    vo.order_id,
                    DATE(vo.order_date),
                    vo.shipping_cost
            ),
            daily_orders AS (
                SELECT
                    date,
                    COUNT(*) AS orders,
                    SUM(revenue) AS revenue,
                    SUM(product_cost) AS product_cost,
                    SUM(shipping_cost) AS shipping
                FROM order_totals
                GROUP BY date
            ),
            daily_ads AS (
                SELECT
                    DATE(expense_date) AS date,
                    SUM(amount) AS ads
                FROM expenses
                WHERE category = 'Meta Ads'
                  AND (%s IS NULL OR DATE(expense_date) >= %s)
                  AND (%s IS NULL OR DATE(expense_date) <= %s)
                GROUP BY DATE(expense_date)
            ),
            report_dates AS (
                SELECT date FROM daily_orders
                UNION
                SELECT date FROM daily_ads
            )
            SELECT
                rd.date,
                COALESCE(daily_order_totals.orders, 0),
                COALESCE(daily_order_totals.revenue, 0),
                COALESCE(daily_order_totals.product_cost, 0),
                COALESCE(daily_order_totals.shipping, 0),
                COALESCE(da.ads, 0)
            FROM report_dates rd
            LEFT JOIN daily_orders AS daily_order_totals
                ON daily_order_totals.date = rd.date
            LEFT JOIN daily_ads da ON da.date = rd.date
            ORDER BY rd.date DESC;
        """, (
            start_date, start_date,
            end_date, end_date,
            start_date, start_date,
            end_date, end_date
        ))

        results = cursor.fetchall()
        daily_data = []

        for row in results:
            report_date = row[0]
            orders = row[1]
            revenue = float(row[2])
            product_cost = float(row[3])
            shipping = float(row[4])
            ads = float(row[5])

            profit_before_ads = revenue - product_cost - shipping
            net_profit = profit_before_ads - ads

            daily_data.append({
                "date": report_date,
                "orders": orders,
                "revenue": revenue,
                "product_cost": product_cost,
                "shipping": shipping,
                "profit_before_ads": profit_before_ads,
                "ads": ads,
                "net_profit": net_profit
            })

        return {"daily": daily_data}

    finally:
        cursor.close()
        connection.close()



@app.get("/analytics/orders")
def get_order_metrics():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            WITH valid_orders AS (
                SELECT o.order_id
                FROM orders o
                WHERE o.order_status NOT IN ('Cancelled', 'Refunded')
                  AND EXISTS (
                      SELECT 1
                      FROM payments p
                      WHERE p.order_id = o.order_id
                        AND p.payment_status = 'Paid'
                  )
            ),
            order_totals AS (
                SELECT
                    vo.order_id,
                    SUM(
                        (oi.quantity * oi.unit_price)
                        - oi.discount_amount
                    ) AS revenue
                FROM valid_orders vo
                JOIN order_items oi
                    ON oi.order_id = vo.order_id
                GROUP BY vo.order_id
            )
            SELECT
                COUNT(*),
                COALESCE(AVG(revenue), 0)
            FROM order_totals;
        """)

        result = cursor.fetchone()

        return {
            "total_orders": result[0],
            "average_order_value": round(float(result[1]), 2)
        }

    finally:
        cursor.close()
        connection.close()
