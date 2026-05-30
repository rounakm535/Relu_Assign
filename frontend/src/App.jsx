import React, { useState, useEffect } from 'react'
import { 
  Globe, Search, Mail, Phone, MapPin, Sparkles, Copy, 
  Check, Database, AlertCircle, Grid, Table, ExternalLink, RefreshCw
} from 'lucide-react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  // State variables
  const [urlInput, setUrlInput] = useState('')
  const [websiteNameInput, setWebsiteNameInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [enrichResult, setEnrichResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  
  // Dashboard Results
  const [resultsList, setResultsList] = useState([])
  const [showDashboard, setShowDashboard] = useState(false)
  const [dashboardView, setDashboardView] = useState('table') // 'table' | 'card'
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Copy to clipboard notification
  const [copied, setCopied] = useState(false)

  // Fetch all results on load if dashboard is open
  useEffect(() => {
    if (showDashboard) {
      fetchHistory()
    }
  }, [showDashboard])

  const validateUrl = (str) => {
    // Basic prefixing if not present
    let url = str.trim()
    if (!/^https?:\/\//i.test(url)) {
      url = 'https://' + url
    }
    try {
      new URL(url)
      return true
    } catch (_) {
      return false
    }
  }

  const handleEnrich = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')
    
    if (!urlInput.trim()) {
      setErrorMsg('Please enter a website URL.')
      return
    }

    if (!validateUrl(urlInput)) {
      setErrorMsg('Please enter a valid URL (e.g. example.com or https://example.com).')
      return
    }

    setLoading(true)
    setEnrichResult(null)

    try {
      const response = await fetch(`${API_BASE_URL}/enrich`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          url: urlInput.trim(),
          website_name: websiteNameInput.trim() || undefined
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to enrich company website.')
      }

      const data = await response.json()
      setEnrichResult(data)
      setSuccessMsg('Company enriched successfully!')
      
      // If dashboard is open, refresh history in background
      if (showDashboard) {
        fetchHistory()
      }
    } catch (err) {
      console.error(err)
      setErrorMsg(err.message || 'An unexpected error occurred while communicating with the server.')
    } finally {
      setLoading(false)
    }
  }

  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      const response = await fetch(`${API_BASE_URL}/results`)
      if (!response.ok) {
        throw new Error('Failed to fetch historical enrichments.')
      }
      const data = await response.json()
      setResultsList(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleCopyOpener = (text) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSelectHistorical = (company) => {
    setEnrichResult(company)
    // Scroll smoothly to details card
    const targetElement = document.getElementById('details-section')
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <div className="app-container">
      {/* Header (SEO Structured) */}
      <header>
        <h1>Company Enrichment Engine</h1>
        <p>
          Transform plain URLs into comprehensive business intelligence. Get instant access to company details, core services, target profiles, and custom cold outreach messages.
        </p>
      </header>

      <main>
        {/* URL Enrichment Input Card */}
        <section className="glass-card" aria-label="Company URL Input Form">
          <form onSubmit={handleEnrich} className="enrich-form" id="enrich-form">
            <div className="input-grid-fields">
              <div className="input-group">
                <Globe className="input-icon" size={20} />
                <input
                  id="url-input"
                  type="text"
                  placeholder="Enter Company URL (e.g. stripe.com)..."
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  className="enrich-input"
                  disabled={loading}
                />
              </div>
              <div className="input-group">
                <Search className="input-icon" size={20} />
                <input
                  id="website-name-input"
                  type="text"
                  placeholder="Website / Company Name (Optional)..."
                  value={websiteNameInput}
                  onChange={(e) => setWebsiteNameInput(e.target.value)}
                  className="enrich-input"
                  disabled={loading}
                />
              </div>
            </div>
            <button 
              id="enrich-submit-btn"
              type="submit" 
              className="glow-button"
              disabled={loading}
            >
              {loading ? (
                <>
                  <RefreshCw className="spinner" size={18} style={{ animation: 'spin 1s linear infinite' }} />
                  Enriching...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Analyze Website
                </>
              )}
            </button>
          </form>
        </section>

        {/* Notifications and Banners */}
        {errorMsg && (
          <div className="alert-banner error" role="alert" id="error-banner">
            <AlertCircle size={20} />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="alert-banner success" role="alert" id="success-banner">
            <Check size={20} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Spinner Loader when fetching first-time */}
        {loading && (
          <div className="glass-card loading-overlay" id="loading-overlay">
            <div className="spinner spinner-glow"></div>
            <p>Crawling website sitemaps, extracting contact details, and inferring business analytics...</p>
          </div>
        )}

        {/* Details Results Card (Subtask 1 Output Display) */}
        {enrichResult && !loading && (
          <section className="glass-card" id="details-section" aria-label="Company Details Results">
            <div className="result-header">
              <div>
                <h2>{enrichResult.company_name || enrichResult.website_name || 'Enriched Profile'}</h2>
                <a href={enrichResult.website_url} target="_blank" rel="noopener noreferrer" className="url-link" id="url-external-link">
                  {enrichResult.website_url} <ExternalLink size={14} style={{ display: 'inline', marginLeft: '4px' }} />
                </a>
              </div>
              <button 
                id="toggle-dashboard-top-btn"
                className="secondary-button" 
                onClick={() => setShowDashboard(!showDashboard)}
              >
                <Database size={16} />
                {showDashboard ? 'Hide Database' : 'View Database'}
              </button>
            </div>

            <div className="result-grid">
              {/* Left Column: Scraping / Contacts (Strict Regex Extracted) */}
              <div className="info-section">
                <h3 className="card-subtitle">🌐 Scraped Contact Information</h3>
                
                <div className="contact-pill-list">
                  <div className="insight-title">Verified Email Addresses (Regex)</div>
                  {enrichResult.mail && enrichResult.mail.length > 0 ? (
                    enrichResult.mail.map((email, idx) => (
                      <div key={idx} className="contact-pill">
                        <Mail className="pill-icon" size={16} />
                        <span>{email}</span>
                      </div>
                    ))
                  ) : (
                    <div className="contact-pill empty">
                      <Mail className="pill-icon" size={16} />
                      <span>No email addresses detected on website</span>
                    </div>
                  )}

                  <div className="insight-title">Phone Number (Regex)</div>
                  {enrichResult.mobile_number ? (
                    <div className="contact-pill">
                      <Phone className="pill-icon" size={16} />
                      <span>{enrichResult.mobile_number}</span>
                    </div>
                  ) : (
                    <div className="contact-pill empty">
                      <Phone className="pill-icon" size={16} />
                      <span>No phone numbers detected on website</span>
                    </div>
                  )}

                  <div className="insight-title">Office Address (Regex)</div>
                  {enrichResult.address ? (
                    <div className="contact-pill">
                      <MapPin className="pill-icon" size={16} />
                      <span>{enrichResult.address}</span>
                    </div>
                  ) : (
                    <div className="contact-pill empty">
                      <MapPin className="pill-icon" size={16} />
                      <span>No physical addresses detected on website</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Business Insights (Inferred via AI) */}
              <div className="info-section">
                <h3 className="card-subtitle">✨ AI Business Intelligence</h3>
                
                <div className="insight-card">
                  <div className="insight-title">Core Service & Product</div>
                  <div className="insight-content">{enrichResult.core_service || 'N/A'}</div>
                </div>

                <div className="insight-card secondary">
                  <div className="insight-title">Target Customer Profile</div>
                  <div className="insight-content">{enrichResult.target_customer || 'N/A'}</div>
                </div>

                <div className="insight-card accent">
                  <div className="insight-title">Probable Pain Points</div>
                  <div className="insight-content">{enrichResult.probable_pain_point || 'N/A'}</div>
                </div>
              </div>
            </div>

            {/* Custom Email Outreach Opener */}
            <div style={{ marginTop: '2.5rem' }}>
              <div className="insight-title">Personalized Outreach Email Opener</div>
              <div className="opener-container" id="opener-container">
                <p className="opener-text">
                  "{enrichResult.outreach_opener || 'Outreach opener could not be generated.'}"
                </p>
                <button 
                  id="copy-opener-btn"
                  className="copy-icon-btn"
                  onClick={() => handleCopyOpener(enrichResult.outreach_opener)}
                  title="Copy to Clipboard"
                >
                  {copied ? <Check size={18} style={{ color: 'var(--color-secondary)' }} /> : <Copy size={18} />}
                </button>
              </div>
            </div>
          </section>
        )}

        {/* Database Dashboard View Toggle */}
        <section style={{ textAlign: 'center', marginTop: '1rem' }}>
          {!showDashboard && !enrichResult && (
            <button 
              id="show-all-results-btn"
              className="glow-button" 
              onClick={() => setShowDashboard(true)}
            >
              <Database size={18} />
              Open Results Database
            </button>
          )}
        </section>

        {/* Database Dashboard Section */}
        {showDashboard && (
          <section className="glass-card" id="database-dashboard" aria-label="Results Database Dashboard">
            <div className="results-dashboard-header">
              <h2 className="dashboard-title">Enriched Companies Database</h2>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div className="view-toggle">
                  <button 
                    id="toggle-table-btn"
                    className={`toggle-btn ${dashboardView === 'table' ? 'active' : ''}`}
                    onClick={() => setDashboardView('table')}
                    title="Table View"
                  >
                    <Table size={16} />
                  </button>
                  <button 
                    id="toggle-card-btn"
                    className={`toggle-btn ${dashboardView === 'card' ? 'active' : ''}`}
                    onClick={() => setDashboardView('card')}
                    title="Card Grid View"
                  >
                    <Grid size={16} />
                  </button>
                </div>
                <button 
                  id="hide-dashboard-btn"
                  className="secondary-button" 
                  onClick={() => setShowDashboard(false)}
                >
                  Close Database
                </button>
              </div>
            </div>

            {loadingHistory ? (
              <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                <RefreshCw className="spinner" size={24} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 10px' }} />
                <p>Loading records...</p>
              </div>
            ) : resultsList.length === 0 ? (
              <div className="empty-state" id="db-empty-state">
                <Database size={48} />
                <p>No enriched companies found in database yet.</p>
              </div>
            ) : dashboardView === 'table' ? (
              /* Subtask 3 Requirements: Responsive Table View */
              <div className="table-wrapper">
                <table className="results-table" id="results-table">
                  <thead>
                    <tr>
                      <th>Company / Site Name</th>
                      <th>URL</th>
                      <th>Core Service</th>
                      <th>Email (Regex)</th>
                      <th>Phone (Regex)</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultsList.map((company) => (
                      <tr key={company.id}>
                        <td>
                          <strong>{company.company_name || company.website_name || 'N/A'}</strong>
                        </td>
                        <td>
                          <a href={company.website_url} target="_blank" rel="noopener noreferrer" className="url-link">
                            {company.website_url.replace(/^https?:\/\//i, '')}
                          </a>
                        </td>
                        <td style={{ maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {company.core_service || 'N/A'}
                        </td>
                        <td>
                          {company.mail && company.mail.length > 0 ? company.mail[0] : '-'}
                        </td>
                        <td>
                          {company.mobile_number || '-'}
                        </td>
                        <td>
                          <button 
                            className="secondary-button" 
                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                            onClick={() => handleSelectHistorical(company)}
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              /* Subtask 3 Requirements: Card View */
              <div className="results-grid" id="results-grid">
                {resultsList.map((company) => (
                  <div key={company.id} className="dashboard-item-card">
                    <div className="card-head">
                      <div>
                        <div className="card-company-name">{company.company_name || company.website_name || 'N/A'}</div>
                        <a href={company.website_url} target="_blank" rel="noopener noreferrer" className="card-company-url">
                          {company.website_url}
                        </a>
                      </div>
                    </div>
                    
                    <div className="card-details-divider"></div>
                    
                    <div>
                      <div className="insight-title" style={{ fontSize: '0.75rem' }}>Core Service</div>
                      <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {company.core_service || 'N/A'}
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <Mail size={14} className="pill-icon" />
                        <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                          {company.mail && company.mail.length > 0 ? company.mail[0] : 'No emails found'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <Phone size={14} className="pill-icon" />
                        <span>{company.mobile_number || 'No phone found'}</span>
                      </div>
                    </div>

                    <button 
                      className="glow-button" 
                      style={{ padding: '0.6rem', width: '100%', fontSize: '0.85rem' }}
                      onClick={() => handleSelectHistorical(company)}
                    >
                      View Full Details
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

export default App
