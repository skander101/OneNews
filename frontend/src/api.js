const API_BASE = '/api/v1'

export async function fetchStatus() {
  const r = await fetch(`${API_BASE}/status`)
  return r.json()
}

export async function fetchPosts(params = {}) {
  const q = new URLSearchParams()
  if (params.category) q.set('category', params.category)
  if (params.topic) q.set('topic', params.topic)
  if (params.limit) q.set('limit', params.limit)
  if (params.min_score) q.set('min_score', params.min_score)
  const r = await fetch(`${API_BASE}/posts?${q}`)
  return r.json()
}

export async function fetchCategories() {
  const r = await fetch(`${API_BASE}/categories`)
  return r.json()
}
