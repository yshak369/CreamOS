from datetime import date

from fastapi import APIRouter

from ..database import get_cursor
from ..queries import VALID_ORDER_CTES, analytics_params, date_filter, profit_by_period_sql

router = APIRouter(prefix="/analytics", tags=["analytics"])

PROFIT_FIELDS = [
    "revenue",
    "product_cost",
    "shipping",
    "payment_fees",
    "ads",
    "other_expenses",
    "return_shipping_loss",
]


def _money(value):
    return round(float(value or 0), 2)


def _profit_row(row):
    """Turn one profit_by_period_sql row into the API shape."""
    data = {field: _money(row[field]) for field in PROFIT_FIELDS}
    data["orders"] = int(row["orders"])
    data["returned_orders"] = int(row["returned_orders"])
    data["profit_before_ads"] = round(
        data["revenue"] - data["product_cost"] - data["shipping"], 2
    )
    data["net_profit"] = round(
        data["revenue"]
        - data["product_cost"]
        - data["shipping"]
        - data["payment_fees"]
        - data["ads"]
        - data["other_expenses"]
        - data["return_shipping_loss"],
        2,
    )
    return data


@router.get("/summary")
def get_analytics_summary(start_date: date = None, end_date: date = None):
    """Whole-period profit and loss.

    net_profit = revenue - product_cost - shipping - payment_fees - ads
                 - other_expenses - return_shipping_loss
    """
    with get_cursor() as cursor:
        cursor.execute(
            profit_by_period_sql(None), analytics_params(start_date, end_date)
        )
        row = cursor.fetchone()

    if row is None:
        row = {field: 0 for field in PROFIT_FIELDS}
        row.update(orders=0, returned_orders=0)

    data = _profit_row(row)
    data.pop("profit_before_ads")
    return data


@router.get("/monthly")
def get_monthly_analytics(start_date: date = None, end_date: date = None):
    with get_cursor() as cursor:
        cursor.execute(
            profit_by_period_sql("month"), analytics_params(start_date, end_date)
        )
        rows = cursor.fetchall()

    return {
        "monthly": [
            {"month": row["period"].strftime("%Y-%m"), **_profit_row(row)}
            for row in rows
        ]
    }


@router.get("/daily")
def get_daily_metrics(start_date: date = None, end_date: date = None):
    with get_cursor() as cursor:
        cursor.execute(
            profit_by_period_sql("day"), analytics_params(start_date, end_date)
        )
        rows = cursor.fetchall()

    return {
        "daily": [
            {"date": row["period"], **_profit_row(row)}
            for row in rows
        ]
    }


@router.get("/channels")
def get_channel_metrics(start_date: date = None, end_date: date = None):
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            WITH {VALID_ORDER_CTES}
            SELECT
                source,
                COUNT(*) AS total_orders,
                COALESCE(SUM(revenue), 0) AS revenue,
                COALESCE(AVG(revenue), 0) AS average_order_value
            FROM order_totals
            GROUP BY source
            ORDER BY revenue DESC;
            """,
            analytics_params(start_date, end_date),
        )
        rows = cursor.fetchall()

    return {
        "channels": [
            {
                "source": row["source"],
                "total_orders": int(row["total_orders"]),
                "revenue": _money(row["revenue"]),
                "average_order_value": _money(row["average_order_value"]),
            }
            for row in rows
        ]
    }


@router.get("/channel-profit")
def get_channel_profit(start_date: date = None, end_date: date = None):
    """Profit per sales channel before ads and other overheads.

    profit_before_ads = revenue - product_cost - shipping - payment_fees
                        - return_shipping_loss
    Return losses are counted against the channel the order came from, which
    matters for COD-heavy channels.
    """
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            WITH {VALID_ORDER_CTES},
            sales AS (
                SELECT
                    ot.source,
                    COUNT(*) AS total_orders,
                    SUM(ot.revenue) AS revenue,
                    SUM(ot.product_cost) AS product_cost,
                    SUM(ot.shipping_cost) AS shipping,
                    SUM(COALESCE(f.payment_fees, 0)) AS payment_fees
                FROM order_totals ot
                LEFT JOIN order_fees f ON f.order_id = ot.order_id
                GROUP BY ot.source
            ),
            returns AS (
                SELECT
                    o.source,
                    COUNT(*) AS returned_orders,
                    SUM(o.shipping_cost) AS return_shipping_loss
                FROM orders o
                WHERE o.order_status = ANY(%(returned_statuses)s)
                  AND {date_filter("o.order_date")}
                GROUP BY o.source
            )
            SELECT
                COALESCE(s.source, r.source) AS source,
                COALESCE(s.total_orders, 0) AS total_orders,
                COALESCE(s.revenue, 0) AS revenue,
                COALESCE(s.product_cost, 0) AS product_cost,
                COALESCE(s.shipping, 0) AS shipping,
                COALESCE(s.payment_fees, 0) AS payment_fees,
                COALESCE(r.returned_orders, 0) AS returned_orders,
                COALESCE(r.return_shipping_loss, 0) AS return_shipping_loss
            FROM sales s
            FULL OUTER JOIN returns r ON r.source = s.source
            ORDER BY revenue DESC;
            """,
            analytics_params(start_date, end_date),
        )
        rows = cursor.fetchall()

    channels = []
    for row in rows:
        revenue = _money(row["revenue"])
        product_cost = _money(row["product_cost"])
        shipping = _money(row["shipping"])
        payment_fees = _money(row["payment_fees"])
        return_loss = _money(row["return_shipping_loss"])
        total_orders = int(row["total_orders"])
        returned_orders = int(row["returned_orders"])
        shipped = total_orders + returned_orders

        channels.append({
            "source": row["source"],
            "total_orders": total_orders,
            "revenue": revenue,
            "product_cost": product_cost,
            "shipping": shipping,
            "payment_fees": payment_fees,
            "returned_orders": returned_orders,
            "return_rate_percentage": (
                round(returned_orders / shipped * 100, 2) if shipped else 0
            ),
            "return_shipping_loss": return_loss,
            "profit_before_ads": round(
                revenue - product_cost - shipping - payment_fees - return_loss, 2
            ),
        })

    return {"channels": channels}


@router.get("/orders")
def get_order_metrics(start_date: date = None, end_date: date = None):
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            WITH {VALID_ORDER_CTES}
            SELECT
                COUNT(*) AS total_orders,
                COALESCE(AVG(revenue), 0) AS average_order_value
            FROM order_totals;
            """,
            analytics_params(start_date, end_date),
        )
        row = cursor.fetchone()

    return {
        "total_orders": int(row["total_orders"]),
        "average_order_value": _money(row["average_order_value"]),
    }


@router.get("/products")
def get_product_analytics(start_date: date = None, end_date: date = None):
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            WITH {VALID_ORDER_CTES}
            SELECT
                p.product_id,
                p.name,
                SUM(oi.quantity) AS units_sold,
                COUNT(DISTINCT vo.order_id) AS total_orders,
                SUM(oi.quantity * oi.unit_price - oi.discount_amount) AS revenue,
                SUM(oi.quantity * oi.unit_cost) AS product_cost
            FROM valid_orders vo
            JOIN order_items oi ON oi.order_id = vo.order_id
            JOIN products p ON p.product_id = oi.product_id
            GROUP BY p.product_id, p.name
            ORDER BY revenue DESC;
            """,
            analytics_params(start_date, end_date),
        )
        rows = cursor.fetchall()

    products = []
    for row in rows:
        revenue = _money(row["revenue"])
        product_cost = _money(row["product_cost"])
        products.append({
            "product_id": row["product_id"],
            "product": row["name"],
            "units_sold": int(row["units_sold"] or 0),
            "total_orders": int(row["total_orders"] or 0),
            "revenue": revenue,
            "product_cost": product_cost,
            "profit_before_shipping_and_ads": round(revenue - product_cost, 2),
            "product_margin_percentage": (
                round((revenue - product_cost) / revenue * 100, 2)
                if revenue > 0 else 0
            ),
        })

    return {"products": products}


@router.get("/customers")
def get_customer_analytics(start_date: date = None, end_date: date = None):
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            WITH {VALID_ORDER_CTES}
            SELECT
                c.customer_id,
                c.name,
                COUNT(ot.order_id) AS total_orders,
                COALESCE(SUM(ot.revenue), 0) AS revenue,
                COALESCE(AVG(ot.revenue), 0) AS average_order_value
            FROM order_totals ot
            JOIN customers c ON c.customer_id = ot.customer_id
            GROUP BY c.customer_id, c.name
            ORDER BY revenue DESC;
            """,
            analytics_params(start_date, end_date),
        )
        rows = cursor.fetchall()

    return {
        "customers": [
            {
                "customer_id": row["customer_id"],
                "customer": row["name"],
                "total_orders": int(row["total_orders"]),
                "revenue": _money(row["revenue"]),
                "average_order_value": _money(row["average_order_value"]),
            }
            for row in rows
        ]
    }


@router.get("/customer-retention")
def get_customer_retention(start_date: date = None, end_date: date = None):
    with get_cursor() as cursor:
        cursor.execute(
            f"""
            WITH {VALID_ORDER_CTES},
            customer_summary AS (
                SELECT
                    customer_id,
                    COUNT(*) AS total_orders,
                    SUM(revenue) AS lifetime_revenue
                FROM order_totals
                GROUP BY customer_id
            )
            SELECT
                COUNT(*) AS total_customers,
                COUNT(*) FILTER (WHERE total_orders > 1) AS repeat_customers,
                COALESCE(SUM(lifetime_revenue), 0) AS total_revenue
            FROM customer_summary;
            """,
            analytics_params(start_date, end_date),
        )
        row = cursor.fetchone()

    total_customers = int(row["total_customers"])
    repeat_customers = int(row["repeat_customers"])

    return {
        "total_customers": total_customers,
        "repeat_customers": repeat_customers,
        "one_time_customers": total_customers - repeat_customers,
        "repeat_customer_rate_percentage": (
            round(repeat_customers / total_customers * 100, 2)
            if total_customers > 0 else 0
        ),
        "total_customer_revenue": _money(row["total_revenue"]),
    }
