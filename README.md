# CreamOS

CreamOS is an end-to-end E-commerce Business Intelligence and AI Platform built for a real-world e-commerce business (CreamXEmirates).

The goal is to turn raw business data from orders, payments, expenses, customers, and marketing into actionable business insights.

## 🚀 Project Goals

CreamOS will help answer questions such as:

- How much revenue did the business generate?
- What is the actual profit?
- Which products and bundles are most profitable?
- Which sales channels perform best?
- How much is being spent on advertising?
- What is the customer acquisition cost?
- Which customers are likely to purchase again?
- What should the business do next to improve profitability?

## 🧩 Main Modules

### 1. Business & Profit Analytics
- Revenue tracking
- Product costs
- Shipping costs
- Payment fees
- Advertising and other expenses
- Losses from returned (RTO) orders
- Daily and monthly profit/loss
- Channel profitability

### 2. Customer & Marketing Intelligence
- Customer segmentation
- Customer lifetime value
- Repeat purchase analysis
- Marketing performance
- Customer behavior analysis
- Machine learning predictions

### 3. AI Business Analyst
- Natural language business questions
- Automated business insights
- AI-generated recommendations
- RAG-based business knowledge system
- SQL/data analysis integration

## 🏗️ Technology Stack

- **Database:** PostgreSQL
- **Backend:** Python, FastAPI, psycopg2, Pydantic
- **Frontend:** React 19 + Vite
- **Testing:** pytest
- **Planned:** Pandas, Scikit-learn, LLMs, RAG, Shopify API, Meta Ads API, Razorpay API

## 📁 Project Structure

```
backend/
  main.py           App setup, CORS, error handling
  database.py       Connection pool and transaction helper
  schemas.py        Request models and allowed status values
  queries.py        Shared analytics SQL ("valid orders", profit and loss)
  routers/          customers, products, orders, payments, expenses, analytics
database/
  schema.sql        Full schema for a new database
  migrations/       Upgrades for an existing database
frontend/           React dashboard
tests/              API tests (run against a throwaway database)
```

## ⚙️ Setup

### 1. Database

New database:

```bash
createdb creamos
psql -d creamos -f database/schema.sql
```

Existing database created from an older `schema.sql`: run the migrations instead (safe to run more than once):

```bash
psql -d creamos -f database/migrations/001_sync_schema_with_backend.sql
```

### 2. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env, then edit it
uvicorn backend.main:app --reload
```

Run `uvicorn` from the project root (not from inside `backend/`). The API runs at http://127.0.0.1:8000 and interactive docs are at http://127.0.0.1:8000/docs.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard runs at http://localhost:5173. Set `VITE_API_BASE_URL` if the API is not on `http://127.0.0.1:8000`.

### 4. Tests

The tests wipe their database, so they only run against the one named in `TEST_DB_NAME`:

```bash
pip install -r requirements-dev.txt
createdb creamos_test
set TEST_DB_NAME=creamos_test   # macOS/Linux: export TEST_DB_NAME=creamos_test
pytest
```

## 📐 How the numbers are calculated

- **Valid (sales) order:** has a payment with status `Paid` and an order status other than `Cancelled`, `Refunded`, `Returned` or `RTO`.
- **Revenue:** quantity × unit price − discount, over valid orders. Shipping is treated as the seller's cost, not charged to the customer.
- **Net profit:** revenue − product cost − shipping − payment gateway fees − ads − other expenses − return shipping loss.
- **Ads:** expenses in the categories `Meta Ads`, `Google Ads` or `Advertising` (any capitalisation). Every other category counts as **other expenses**.
- **Return shipping loss:** the shipping cost of orders marked `Returned` or `RTO`. Record any extra return courier charges as an expense.

Status values are matched case-insensitively and stored in a standard spelling:

- **Order status:** Placed, Confirmed, Processing, Shipped, Delivered, Cancelled, Returned, RTO, Refunded
- **Payment status:** Paid, Pending, Failed, Refunded

When a `Paid` payment is recorded for an order (for example cash collected on a COD order), the order's payment status is updated to `Paid`.

## 🔌 API Overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST / GET | `/customers` | Add / list customers |
| POST / GET | `/products` | Add / list products |
| POST / GET | `/orders` | Create an order (items + optional payment) / list orders |
| POST / GET | `/payments` | Record / list payments |
| POST / GET | `/expenses` | Record / list expenses |
| GET | `/analytics/summary` | Profit and loss for a period |
| GET | `/analytics/monthly`, `/analytics/daily` | Profit and loss by month / day |
| GET | `/analytics/channels`, `/analytics/channel-profit` | Sales and profit by channel, incl. return rate |
| GET | `/analytics/products` | Product revenue and margin |
| GET | `/analytics/customers`, `/analytics/customer-retention` | Customer value and repeat rate |

Analytics endpoints accept optional `start_date` and `end_date` (YYYY-MM-DD, inclusive). When creating an order, `unit_price` and `unit_cost` may be left out to use the product's current prices.

## 📊 Current Progress

- [x] PostgreSQL database and schema
- [x] Revenue, cost, shipping, fee and full profit calculation
- [x] FastAPI backend and REST APIs
- [x] Analytics layer (summary, daily, monthly, channels, products, customers, retention)
- [x] Business dashboard (React)
- [x] Automated API tests

### Upcoming

- [ ] Authentication (required before deploying anywhere public: the API exposes customer details)
- [ ] Trend charts on the dashboard (monthly / channel)
- [ ] Shopify integration
- [ ] Meta Ads integration
- [ ] Razorpay integration
- [ ] Customer analytics and segmentation
- [ ] Machine learning
- [ ] RAG system
- [ ] AI Business Analyst

## 🎯 Vision

CreamOS is being developed as a production-oriented portfolio project using real business requirements and real-world e-commerce data structures.

The long-term goal is to create an intelligent system that can understand the business, analyze its performance, identify problems, and recommend actions.
