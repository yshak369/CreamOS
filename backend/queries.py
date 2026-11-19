"""SQL shared by the analytics endpoints.

Every analytics query starts from the same definition of a "valid" order, so
it lives here once instead of being copied into each endpoint.

Queries use named parameters; build them with analytics_params().
"""

from .schemas import AD_EXPENSE_CATEGORIES, EXCLUDED_ORDER_STATUSES, RETURNED_ORDER_STATUSES


def analytics_params(start_date=None, end_date=None):
    return {
        "start_date": start_date,
        "end_date": end_date,
        "excluded_statuses": EXCLUDED_ORDER_STATUSES,
        "returned_statuses": RETURNED_ORDER_STATUSES,
        "ad_categories": AD_EXPENSE_CATEGORIES,
    }


def date_filter(column):
    """Inclusive start_date / end_date filter on a timestamp column.

    Compares the raw column (not DATE(column)) so indexes can be used.
    """
    return f"""
        (%(start_date)s::date IS NULL OR {column} >= %(start_date)s::date)
        AND (%(end_date)s::date IS NULL OR {column} < %(end_date)s::date + 1)
    """


# A valid order is not cancelled/refunded/returned and has a Paid payment.
# order_totals adds each valid order's revenue and product cost.
VALID_ORDER_CTES = f"""
    valid_orders AS (
        SELECT
            o.order_id,
            o.customer_id,
            o.order_date,
            o.source,
            o.shipping_cost
        FROM orders o
        WHERE o.order_status <> ALL(%(excluded_statuses)s)
          AND {date_filter("o.order_date")}
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
            vo.customer_id,
            vo.order_date,
            vo.source,
            vo.shipping_cost,
            SUM((oi.quantity * oi.unit_price) - oi.discount_amount) AS revenue,
            SUM(oi.quantity * oi.unit_cost) AS product_cost
        FROM valid_orders vo
        JOIN order_items oi ON oi.order_id = vo.order_id
        GROUP BY
            vo.order_id, vo.customer_id, vo.order_date,
            vo.source, vo.shipping_cost
    ),
    order_fees AS (
        SELECT
            vo.order_id,
            SUM(p.gateway_fee) AS payment_fees
        FROM valid_orders vo
        JOIN payments p ON p.order_id = vo.order_id
        WHERE p.payment_status = 'Paid'
        GROUP BY vo.order_id
    )
"""


def profit_by_period_sql(period):
    """Full profit and loss, grouped by period.

    period: "month", "day", or None (one row for the whole range).
    """
    def bucket(column):
        if period == "month":
            return f"DATE_TRUNC('month', {column})::date"
        if period == "day":
            return f"DATE({column})"
        return "1"

    return f"""
        WITH {VALID_ORDER_CTES},
        sales AS (
            SELECT
                {bucket("ot.order_date")} AS period,
                COUNT(*) AS orders,
                SUM(ot.revenue) AS revenue,
                SUM(ot.product_cost) AS product_cost,
                SUM(ot.shipping_cost) AS shipping,
                SUM(COALESCE(f.payment_fees, 0)) AS payment_fees
            FROM order_totals ot
            LEFT JOIN order_fees f ON f.order_id = ot.order_id
            GROUP BY 1
        ),
        expense_totals AS (
            SELECT
                {bucket("e.expense_date")} AS period,
                SUM(e.amount) FILTER (
                    WHERE LOWER(e.category) = ANY(%(ad_categories)s)
                ) AS ads,
                SUM(e.amount) FILTER (
                    WHERE NOT (LOWER(e.category) = ANY(%(ad_categories)s))
                ) AS other_expenses
            FROM expenses e
            WHERE {date_filter("e.expense_date")}
            GROUP BY 1
        ),
        returns AS (
            SELECT
                {bucket("o.order_date")} AS period,
                COUNT(*) AS returned_orders,
                SUM(o.shipping_cost) AS return_shipping_loss
            FROM orders o
            WHERE o.order_status = ANY(%(returned_statuses)s)
              AND {date_filter("o.order_date")}
            GROUP BY 1
        ),
        periods AS (
            SELECT period FROM sales
            UNION SELECT period FROM expense_totals
            UNION SELECT period FROM returns
        )
        SELECT
            pr.period,
            COALESCE(s.orders, 0) AS orders,
            COALESCE(s.revenue, 0) AS revenue,
            COALESCE(s.product_cost, 0) AS product_cost,
            COALESCE(s.shipping, 0) AS shipping,
            COALESCE(s.payment_fees, 0) AS payment_fees,
            COALESCE(et.ads, 0) AS ads,
            COALESCE(et.other_expenses, 0) AS other_expenses,
            COALESCE(r.returned_orders, 0) AS returned_orders,
            COALESCE(r.return_shipping_loss, 0) AS return_shipping_loss
        FROM periods pr
        LEFT JOIN sales s ON s.period = pr.period
        LEFT JOIN expense_totals et ON et.period = pr.period
        LEFT JOIN returns r ON r.period = pr.period
        ORDER BY pr.period DESC
    """
