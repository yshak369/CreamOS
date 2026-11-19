from fastapi import APIRouter

from ..database import get_cursor
from ..schemas import ExpenseCreate

router = APIRouter(tags=["expenses"])


@router.post("/expenses")
def create_expense(expense: ExpenseCreate):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO expenses (expense_date, category, amount, description)
            VALUES (COALESCE(%s, CURRENT_TIMESTAMP), %s, %s, %s)
            RETURNING expense_id;
            """,
            (
                expense.expense_date,
                expense.category,
                expense.amount,
                expense.description,
            ),
        )
        expense_id = cursor.fetchone()["expense_id"]

    return {"message": "Expense recorded successfully", "expense_id": expense_id}


@router.get("/expenses")
def get_expenses():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT expense_id, expense_date, category, amount, description
            FROM expenses
            ORDER BY expense_date DESC;
            """
        )
        rows = cursor.fetchall()

    return {
        "expenses": [
            {**row, "amount": float(row["amount"])}
            for row in rows
        ]
    }
