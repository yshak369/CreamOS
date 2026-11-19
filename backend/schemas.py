"""Request models and the allowed status values.

Status values are matched case-insensitively ("paid", "PAID" and "Paid" all
become "Paid") so that differently typed values can no longer slip past the
analytics, which only count the canonical spelling.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class _CaseInsensitiveEnum(str, Enum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            wanted = value.strip().lower()
            for member in cls:
                if member.value.lower() == wanted:
                    return member
        return None


class PaymentStatus(_CaseInsensitiveEnum):
    PAID = "Paid"
    PENDING = "Pending"
    FAILED = "Failed"
    REFUNDED = "Refunded"


class OrderStatus(_CaseInsensitiveEnum):
    PLACED = "Placed"
    CONFIRMED = "Confirmed"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"
    RETURNED = "Returned"
    RTO = "RTO"  # returned to origin (e.g. a COD parcel the customer refused)
    REFUNDED = "Refunded"


# Orders in these statuses never count as sales.
EXCLUDED_ORDER_STATUSES = [
    OrderStatus.CANCELLED.value,
    OrderStatus.REFUNDED.value,
    OrderStatus.RETURNED.value,
    OrderStatus.RTO.value,
]

# Orders in these statuses were shipped and came back: the shipping spent on
# them is a loss.
RETURNED_ORDER_STATUSES = [
    OrderStatus.RETURNED.value,
    OrderStatus.RTO.value,
]

# Expense categories reported as "ads" (compared in lower case). Every other
# expense category is reported as "other_expenses". Both reduce net profit.
AD_EXPENSE_CATEGORIES = ["meta ads", "google ads", "advertising"]


Money = Decimal


class _Stripped(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _strip_strings(cls, value):
        return value.strip() if isinstance(value, str) else value


class CustomerCreate(_Stripped):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    address: str = Field(min_length=1)
    pincode: str = Field(min_length=1, max_length=10)


class ProductCreate(_Stripped):
    name: str = Field(min_length=1, max_length=100)
    selling_price: Money = Field(ge=0, max_digits=10, decimal_places=2)
    cost_price: Money = Field(ge=0, max_digits=10, decimal_places=2)


class ExpenseCreate(_Stripped):
    category: str = Field(min_length=1, max_length=50)
    amount: Money = Field(ge=0, max_digits=10, decimal_places=2)
    description: str | None = None
    expense_date: datetime | None = None


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    # Leave out to use the product's current selling/cost price.
    unit_price: Money | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    unit_cost: Money | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    discount_amount: Money = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)


class OrderPaymentCreate(_Stripped):
    amount: Money = Field(ge=0, max_digits=10, decimal_places=2)
    payment_method: str = Field(min_length=1, max_length=50)
    payment_status: PaymentStatus
    gateway: str | None = None
    transaction_id: str | None = None
    gateway_fee: Money = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)


class PaymentCreate(OrderPaymentCreate):
    order_id: int


class OrderCreate(_Stripped):
    customer_id: int
    source: str = Field(min_length=1, max_length=50)
    payment_method: str = Field(min_length=1, max_length=50)
    payment_status: PaymentStatus
    order_status: OrderStatus
    shipping_cost: Money = Field(default=Decimal("50"), ge=0, max_digits=10, decimal_places=2)
    items: list[OrderItemCreate] = Field(min_length=1)
    payment: OrderPaymentCreate | None = None
