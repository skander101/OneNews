import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchCategories, fetchPosts, fetchStatus } from './api'

const CAT_LABELS = {
  government: '\u{1F3DB}\uFE0F Government',
  conglomerate: '\u{1F3E2} Media Conglomerate',
  private_equity: '\u{1F4B0} Private Equity',
  wealthy_private: '\u{1F464} Wealthy Private Owner',
  corporate: '\u{1F4CA} Corporate',
  independent: '\u2705 Independent',
}

function groupByDate(clusters) {
  const getDate = (c) => c.articles[0]?.published_iso || ''
  const getDisplay = (c) => c.articles[0]?.published || 'Unknown'
  const map = {}
  for (const c of clusters) {
    const key = getDate(c)
    if (!map[key]) map[key] = { display: getDisplay(c), items: [] }
    map[key].items.push(c)
  }
  const sorted = Object.entries(map).sort((a, b) => {
    if (!a[0]) return 1
    if (!b[0]) return -1
    return b[0].localeCompare(a[0])
  })
  return sorted.map(([, group]) => ({
    date: group.display,
    items: group.items.sort((a, b) => (b.final_score || 0) - (a.final_score || 0)),
  }))
}

function SafeImage({ src, className, wrapClass }) {
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    return <div className="card-image-placeholder">{'\u{1F4F0}'}</div>
  }
  return (
    <div className={wrapClass}>
      <img className={className} src={src} alt="" loading="lazy" onError={() => setFailed(true)} />
    </div>
  )
}

function ScoreBar({ score }) {
  const barRef = useRef(null)
  const animated = useRef(false)

  useEffect(() => {
    if (animated.current) return
    const el = barRef.current
    if (!el) return

    const reveal = () => {
      if (animated.current) return
      animated.current = true
      const target = score * 100
      el.style.width = '0%'
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          el.style.width = target + '%'
        })
      })
    }

    const parent = el.closest('.card')
    if (parent && parent.classList.contains('revealed')) {
      reveal()
    } else {
      const obs = new MutationObserver(() => {
        if (parent && parent.classList.contains('revealed')) {
          reveal()
          obs.disconnect()
        }
      })
      if (parent) obs.observe(parent, { attributes: true, attributeFilter: ['class'] })
      return () => obs.disconnect()
    }
  }, [score])

  return (
    <div className="score-bar-wrap">
      <div className="score-bar-fill" ref={barRef}></div>
    </div>
  )
}

export default function App() {
  const [categories, setCategories] = useState([])
  const [allClusters, setAllClusters] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState(0)
  const [status, setStatus] = useState('starting')
  const [total, setTotal] = useState(0)
  const [sponsorInfo, setSponsorInfo] = useState(null)
  const tabsRef = useRef(null)
  const underlineRef = useRef(null)
  const observerRef = useRef(null)

  useEffect(() => {
    Promise.all([fetchCategories(), fetchPosts(), fetchStatus()])
      .then(([catRes, postRes, statusRes]) => {
        setCategories(catRes.categories)
        setAllClusters(postRes.clusters)
        setTotal(postRes.meta.total)
        setStatus(statusRes.pipeline_status)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!underlineRef.current || !tabsRef.current) return
    const tab = tabsRef.current.children[activeTab]
    if (!tab) return
    underlineRef.current.style.left = tab.offsetLeft + 'px'
    underlineRef.current.style.width = tab.offsetWidth + 'px'
  }, [activeTab, categories])

  useEffect(() => {
    observerRef.current = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed')
          observerRef.current.unobserve(entry.target)
        }
      }
    }, { threshold: 0.1, rootMargin: '0px 0px 40px 0px' })
    return () => observerRef.current?.disconnect()
  }, [])

  useEffect(() => {
    if (loading) return
    const timer = setTimeout(() => {
      const tabKey = categories[activeTab]
      if (!tabKey) return
      const tc = document.getElementById('tab-' + tabKey.replace(/[\s/]+/g, '_'))
      if (!tc) return
      tc.querySelectorAll('.card:not(.revealed)').forEach(c => {
        observerRef.current?.observe(c)
      })
    }, 50)
    return () => clearTimeout(timer)
  }, [activeTab, loading, categories])

  useEffect(() => {
    if (loading || total === 0) return
    const el = document.getElementById('count-total')
    if (!el) return
    let current = 0
    const step = Math.max(1, Math.floor(total / 20))
    const interval = setInterval(() => {
      current += step
      if (current >= total) {
        current = total
        clearInterval(interval)
      }
      el.textContent = current
    }, 40)
    return () => clearInterval(interval)
  }, [loading, total])

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') setSponsorInfo(null)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [])

  const tabId = (name) => name.replace(/[\s/]+/g, '_')
  const tabKey = categories[activeTab]
  const filtered = tabKey ? allClusters.filter(c => c.category === tabKey) : []
  const dateGroups = groupByDate(filtered)

  return (
    <>
      <div className="header">
        <div className="header-inner">
          <div>
            <h1>News Digest</h1>
            <span>
              <span id="count-total" data-target={total}>0</span>
              {' stories across '}{categories.length}{' topics'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="status">
              <span className="status-dot"></span>
              {status}
            </span>
          </div>
        </div>
      </div>

      <div className="container">
        {loading ? (
          <div className="grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <div className="card" key={i} style={{ opacity: 1, transform: 'none', borderColor: '#1a1a1a' }}>
                <div className="skeleton skeleton-img"></div>
                <div className="card-body">
                  <div className="skeleton skeleton-text-short"></div>
                  <div className="skeleton skeleton-text"></div>
                  <div className="skeleton skeleton-text" style={{ width: '60%' }}></div>
                  <div style={{ marginTop: 'auto' }}>
                    <div className="skeleton" style={{ height: 4, marginBottom: 3 }}></div>
                    <div className="skeleton skeleton-text-short" style={{ marginBottom: 0 }}></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : total === 0 ? (
          <div className="empty">
            <h2>No news yet</h2>
            <p>Run <code>python webapp.py</code> to fetch and analyze articles</p>
          </div>
        ) : (
          <>
            <div className="tabs" ref={tabsRef}>
              {categories.map((cat, i) => (
                <button
                  key={cat}
                  className={'tab' + (i === activeTab ? ' active' : '')}
                  onClick={() => setActiveTab(i)}
                >
                  {cat}{' '}
                  <span className="tab-count">
                    ({allClusters.filter(c => c.category === cat).length})
                  </span>
                </button>
              ))}
              <div className="tab-underline" ref={underlineRef}></div>
            </div>

            {categories.map((cat, i) => (
              <div
                key={cat}
                id={'tab-' + tabId(cat)}
                style={{ display: i === activeTab ? 'block' : 'none' }}
              >
                {dateGroups.length === 0 ? (
                  <div className="empty"><h2>No {cat} stories found</h2></div>
                ) : (
                  dateGroups.map(group => (
                    <div className="date-group" key={group.date}>
                      <div className="date-header">{group.date}</div>
                      <div className="grid">
                        {group.items.map((c, idx) => {
                          const a = c.articles[0]
                          return (
                            <div className="card" key={c.top_post_url || idx}>
                              <SafeImage
                                src={c.image_url}
                                className="card-image"
                                wrapClass="card-image-wrap"
                              />
                              <div className="card-body">
                                <div className="card-rank">#{idx + 1}</div>
                                <div className="card-topic">{c.topic}</div>
                                <div className="card-title">{a.title}</div>
                                {a.summary && (
                                  <div className="card-summary">
                                    {a.summary.length > 160 ? a.summary.slice(0, 160) + '\u2026' : a.summary}
                                  </div>
                                )}
                                <div className="card-topics">
                                  {(a.topics || []).slice(0, 3).map(t => (
                                    <span className="topic-tag" key={t}>{t}</span>
                                  ))}
                                </div>
                                <div className="card-meta">
                                  <span className="source">{a.domain}</span>
                                  <span>{'\u{1F6E1}\uFE0F'} {c.avg_trustworthiness != null ? (c.avg_trustworthiness * 100).toFixed(0) + '%' : ''}</span>
                                  {a.article_leaning && (
                                    <span className={'bias-badge bias-' + a.article_leaning}>{a.article_leaning}</span>
                                  )}
                                  {a.source_bias && a.source_bias !== a.article_leaning && (
                                    <span style={{ fontSize: 9, color: '#64748b' }}>src:{a.source_bias}</span>
                                  )}
                                  {a.source_factuality && (
                                    <span className={'factuality-badge factuality-' + a.source_factuality}>{a.source_factuality}</span>
                                  )}
                                  {c.total_coverage > 1 && <span>{'\u{1F4F0}'} {c.total_coverage}</span>}
                                  {a.sponsor && <span className="sponsor">{'\u{1F3E2}'} {a.sponsor}</span>}
                                </div>
                                <ScoreBar score={c.final_score} />
                                <div className="score-label">
                                  <span>Relevance</span>
                                  <span>{c.final_score}</span>
                                </div>
                                <div className="card-actions">
                                  <button className="btn btn-primary" onClick={() => setSponsorInfo(a.sponsor_info)}>
                                    {'\u{1F3E2}'} Sponsors
                                  </button>
                                  <a href={c.top_post_url} className="btn btn-secondary" target="_blank">Open</a>
                                  {a.published && <span className="card-date">{a.published}</span>}
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  ))
                )}
              </div>
            ))}
          </>
        )}
      </div>

      <div
        className={'modal-overlay' + (sponsorInfo ? ' active' : '')}
        onClick={(e) => { if (e.target === e.currentTarget) setSponsorInfo(null) }}
      >
        <div className="modal">
          <button className="modal-close" onClick={() => setSponsorInfo(null)}>{'\u2715'}</button>
          {sponsorInfo ? (
            <>
              <h2>{sponsorInfo.display}</h2>
              <div className="parent">Parent: {sponsorInfo.parent || '\u2014'}</div>
              <div className="modal-row">
                {sponsorInfo.category && (
                  <span className={'category-badge cat-' + sponsorInfo.category}>
                    {CAT_LABELS[sponsorInfo.category] || sponsorInfo.category}
                  </span>
                )}
                {sponsorInfo.bias && (
                  <span className={'bias-badge bias-' + sponsorInfo.bias}>{sponsorInfo.bias}</span>
                )}
                {sponsorInfo.factuality && (
                  <span className={'factuality-badge factuality-' + sponsorInfo.factuality}>{sponsorInfo.factuality}</span>
                )}
              </div>
              {sponsorInfo.owners && sponsorInfo.owners.length > 0 && (
                <div className="modal-section">
                  <h3>Shareholders / Funders</h3>
                  <div className="owner-list">
                    {sponsorInfo.owners.map(o => (
                      <span key={o} style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                        <span className="owner-tag">{o}</span>
                        {sponsorInfo.owner_wikis && sponsorInfo.owner_wikis[o] && (
                          <a href={sponsorInfo.owner_wikis[o]} className="owner-wiki" target="_blank" title="Wikipedia">{'\u{1F4D6}'}</a>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {sponsorInfo.wikipedia && (
                <a href={sponsorInfo.wikipedia} className="modal-wiki" target="_blank">{'\u{1F4D6}'} Wikipedia</a>
              )}
            </>
          ) : (
            <p style={{ color: '#666' }}>No sponsor data available.</p>
          )}
        </div>
      </div>
    </>
  )
}
