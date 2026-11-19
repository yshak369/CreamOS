import './App.css'
import { useEffect, useState } from 'react'
import { fetchAnalytics } from './api'

const EMPTY = '—'

function formatRupees(value) {
  if (value === undefined || value === null) return EMPTY
  const amount = Number(value)
  const digits = Number.isInteger(amount) ? 0 : 2
  return `₹${amount.toLocaleString('en-IN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`
}

function formatPercent(value, digits = 2) {
  if (value === undefined || value === null) return EMPTY
  return `${Number(value).toFixed(digits)}%`
}

function clampPercent(value) {
  return Math.min(100, Math.max(0, Number(value ?? 0)))
}

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning.'
  if (hour < 17) return 'Good afternoon.'
  return 'Good evening.'
}

function App() {
  const [summary, setSummary] = useState(null)
  const [orderMetrics, setOrderMetrics] = useState(null)
  const [productMetrics, setProductMetrics] = useState(null)
  const [customerMetrics, setCustomerMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      fetchAnalytics('/analytics/summary'),
      fetchAnalytics('/analytics/orders'),
      fetchAnalytics('/analytics/products'),
      fetchAnalytics('/analytics/customer-retention'),
    ])
      .then(([summaryData, orderData, productData, customerData]) => {
        setSummary(summaryData)
        setOrderMetrics(orderData)
        setProductMetrics(productData)
        setCustomerMetrics(customerData)
      })
      .catch((err) => {
        console.error('Analytics loading failed:', err)
        setError('Unable to load analytics. Check that the backend is running.')
      })
      .finally(() => setLoading(false))
  }, [])

  const topProduct = productMetrics?.products?.[0]
  const hasProducts = productMetrics?.products?.length > 0

  const metrics = [
    {
      label: 'Total Revenue',
      value: formatRupees(summary?.revenue),
      note: 'Paid orders',
    },
    {
      label: 'Net Profit',
      value: formatRupees(summary?.net_profit),
      note: 'After all recorded costs',
    },
    {
      label: 'Paid Orders',
      value: orderMetrics
        ? Number(orderMetrics.total_orders ?? 0).toLocaleString('en-IN')
        : EMPTY,
      note: 'Valid paid orders',
    },
    {
      label: 'Units Sold',
      value: productMetrics?.products
        ? productMetrics.products
            .reduce(
              (total, product) => total + Number(product.units_sold || 0),
              0
            )
            .toLocaleString('en-IN')
        : EMPTY,
      note: 'Paid product units',
    },
  ]

  const costRows = [
    ['Product costs', summary?.product_cost],
    ['Shipping', summary?.shipping],
    ['Payment fees', summary?.payment_fees],
    ['Advertising', summary?.ads],
    ['Other expenses', summary?.other_expenses],
    ['Returns (RTO) shipping', summary?.return_shipping_loss],
  ]

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">C</div>
          <div>
            <h2>CreamOS</h2>
            <p>Business Intelligence</p>
          </div>
        </div>

        <p className="nav-heading">WORKSPACE</p>
        <nav>
          <a className="nav-item active" href="#overview">Overview</a>
          <a className="nav-item" href="#sales">Profit</a>
          <a className="nav-item" href="#products">Products</a>
          <a className="nav-item" href="#customers">Customers</a>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          CreamXEmirates
          <small>Business workspace</small>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div>
            <p className="eyebrow">BUSINESS OVERVIEW</p>
            <h1>{greeting()}</h1>
            <p className="subtitle">
              Here&apos;s how your business is performing.
            </p>
          </div>
          <div className="profile">
            <div className="profile-avatar">C</div>
            <div>
              <strong>Business Owner</strong>
              <span>CreamXEmirates</span>
            </div>
          </div>
        </header>

        <section className="section-heading">
          <div>
            <h2>Performance overview</h2>
            <p>Your current analytics snapshot</p>
          </div>
          <span className="period-badge">All time</span>
        </section>

        {loading && <p className="status-message">Loading business analytics...</p>}
        {error && (
          <p className="status-message status-error" role="alert">
            {error}
          </p>
        )}

        <section className="metrics-grid">
          {metrics.map((metric) => (
            <article className="metric-card" key={metric.label}>
              <p>{metric.label}</p>
              <h3>{metric.value}</h3>
              <span>{metric.note}</span>
            </article>
          ))}
        </section>

        <section className="content-grid">
          <article className="panel" id="sales">
            <div className="panel-heading">
              <div>
                <h2>Profit summary</h2>
                <p>Revenue after every recorded cost</p>
              </div>
              <span className="panel-icon">₹</span>
            </div>

            <div className="profit-row">
              <span>Revenue</span>
              <strong>{formatRupees(summary?.revenue)}</strong>
            </div>

            {costRows.map(([label, value]) => (
              <div className="profit-row" key={label}>
                <span>{label}</span>
                <strong>
                  {summary ? `− ${formatRupees(value ?? 0)}` : EMPTY}
                </strong>
              </div>
            ))}

            <div className="profit-total">
              <span>Net profit</span>
              <strong>{formatRupees(summary?.net_profit)}</strong>
            </div>
          </article>

          <article className="panel" id="products">
            <div className="panel-heading">
              <div>
                <h2>Product performance</h2>
                <p>Top product by revenue</p>
              </div>
              <span className="panel-icon">↗</span>
            </div>

            <div className="product-card">
              <div className="product-icon">
                {topProduct?.product?.[0]?.toUpperCase() ?? 'C'}
              </div>
              <div className="product-info">
                <strong>
                  {topProduct?.product
                    ?? (loading
                      ? 'Loading...'
                      : productMetrics && !hasProducts
                        ? 'No paid sales yet'
                        : EMPTY)}
                </strong>
                <span>
                  {topProduct ? `${topProduct.units_sold} units sold` : EMPTY}
                </span>
              </div>
              <span className="product-revenue">
                {formatRupees(topProduct?.revenue)}
              </span>
            </div>

            <div className="margin-label">
              <span>Product margin</span>
              <strong>{formatPercent(topProduct?.product_margin_percentage)}</strong>
            </div>

            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${clampPercent(topProduct?.product_margin_percentage)}%`,
                }}
              />
            </div>

            <p className="footnote">
              Before shipping, advertising and payment fees.
            </p>
          </article>
        </section>

        <section className="panel customer-panel" id="customers">
          <div className="panel-heading">
            <div>
              <h2>Customer retention</h2>
              <p>Repeat purchasing in your current data</p>
            </div>
            <span className="retention-value">
              {formatPercent(customerMetrics?.repeat_customer_rate_percentage, 0)}
            </span>
          </div>

          <div className="retention-track">
            <div
              className="retention-fill"
              style={{
                width: `${clampPercent(
                  customerMetrics?.repeat_customer_rate_percentage
                )}%`,
              }}
            />
          </div>

          <div className="retention-footer">
            <span>
              {customerMetrics?.repeat_customers ?? EMPTY} repeat customers
            </span>
            <span>
              {customerMetrics?.total_customers ?? EMPTY} total customers
            </span>
          </div>
        </section>

        <footer>
          CreamOS · Built for smarter business decisions
          <span>Live data from the CreamOS API</span>
        </footer>
      </main>
    </div>
  )
}

export default App
