from fastapi import APIRouter

from ..database import get_cursor
from ..schemas import ProductCreate

router = APIRouter(tags=["products"])


@router.post("/products")
def create_product(product: ProductCreate):
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO products (name, selling_price, cost_price)
            VALUES (%s, %s, %s)
            RETURNING product_id;
            """,
            (product.name, product.selling_price, product.cost_price),
        )
        product_id = cursor.fetchone()["product_id"]

    return {"message": "Product created successfully", "product_id": product_id}


@router.get("/products")
def get_products():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT product_id, name, selling_price, cost_price
            FROM products
            ORDER BY product_id DESC;
            """
        )
        rows = cursor.fetchall()

    return {
        "products": [
            {
                "product_id": row["product_id"],
                "name": row["name"],
                "selling_price": float(row["selling_price"]),
                "cost_price": float(row["cost_price"]),
            }
            for row in rows
        ]
    }
