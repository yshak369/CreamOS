
import './App.css'
import { useEffect, useState } from 'react'
import { fetchAnalytics } from './api'

function App() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [orderMetrics, setOrderMetrics] = useState(null)
  const [productMetrics, setProductMetrics] = useState(null)

  useEffect(() => {
  Promise.all([
    fetchAnalytics('/analytics/summary'),
    fetchAnalytics('/analytics/orders'),
    fetchAnalytics('/analytics/products'),
  ])
    .then(([summaryData, orderData, productData]) => {
      setSummary(summaryData)
      setOrderMetrics(orderData)
      setProductMetrics(productData)
    })
    .catch((err) => {
      console.error('Analytics loading failed:', err)
      setError('Unable to load analytics. Check your backend.')
    })
    .finally(() => setLoading(false))
    }, [])


  const metrics = [
    {
      label: 'Total Revenue',
      value: summary
        ? `₹${Number(summary.revenue).toLocaleString('en-IN')}`
        : '—',
      note: 'Paid orders',
    },
    {
      label: 'Net Profit',
      value: summary
        ? `₹${Number(summary.net_profit).toLocaleString('en-IN')}`
        : '—',
      note: 'After recorded expenses',
    },
    {
      label: 'Paid Orders',
      value: orderMetrics
        ? Number(orderMetrics.total_orders ?? 0).toLocaleString('en-IN')
        : '—',
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
        : '—',
      note: 'Paid product units',
    },
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
          <a className="nav-item" href="#sales">Sales Analytics</a>
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
            <h1>Good morning.</h1>
            <p className="subtitle">
              Here's how your business is performing.
            </p>
          </div>
          <div className="profile">
            <div className="profile-avatar">V</div>
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
          <span className="period-badge">All-time sample data</span>
        </section>


        {loading && <p>Loading business analytics...</p>}
        {error && <p role="alert">{error}</p>}
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
                <p>Revenue after recorded costs</p>
              </div>
              <span className="panel-icon">₹</span>
            </div>

            <div className="profit-row">
              <span>Revenue</span><strong>₹7,794</strong>
            </div>
            <div className="profit-row">
              <span>Product costs</span><strong>− ₹5,000</strong>
            </div>
            <div className="profit-row">
              <span>Shipping</span><strong>− ₹300</strong>
            </div>
            <div className="profit-row">
              <span>Advertising</span><strong>− ₹750</strong>
            </div>
            <div className="profit-row">
              <span>Payment fees</span><strong>− ₹0</strong>
            </div>
            <div className="profit-total">
              <span>Net profit</span><strong>₹1,744</strong>
            </div>
          </article>

          <article className="panel" id="products">
            <div className="panel-heading">
              <div>
                <h2>Product performance</h2>
                <p>Best-selling product</p>
              </div>
              <span className="panel-icon">↗</span>
            </div>

            <div className="product-card">
              <div className="product-icon">C</div>
              <div className="product-info">
                <strong>Cream</strong>
                <span>10 units sold</span>
              </div>
              <span className="product-revenue">₹7,794</span>
            </div>

            <div className="margin-label">
              <span>Product margin</span><strong>35.85%</strong>
            </div>
            <div className="progress-track">
              <div className="progress-fill" />
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
              <p>Repeat purchasing in your current sample data</p>
            </div>
            <span className="retention-value">50%</span>
          </div>
          <div className="retention-track">
            <div className="retention-fill" />
          </div>
          <div className="retention-footer">
            <span>1 repeat customer</span>
            <span>2 total paying customers</span>
          </div>
        </section>

        <footer>
          CreamOS · Built for smarter business decisions
          <span>Dashboard preview · Sample values</span>
        </footer>
      </main>
    </div>
  )
}

export default App
