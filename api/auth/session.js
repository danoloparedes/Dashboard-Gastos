import { session, login, logout, accessResponse, persistentCookie } from '../_lib/auth.js'
export default { async fetch(request) {
  try {
    const headers = { 'Cache-Control': 'no-store' }
    if (request.method === 'GET') {
      const authenticated = await session(request)
      if (authenticated) headers['Set-Cookie'] = persistentCookie(request)
      return Response.json({ authenticated }, { headers })
    }
    if (request.method === 'POST') return Response.json({ authenticated: true }, { headers: { ...headers, 'Set-Cookie': await login(request) } })
    if (request.method === 'DELETE') return Response.json({ authenticated: false }, { headers: { ...headers, 'Set-Cookie': await logout(request) } })
    return Response.json({ error: 'method_not_allowed' }, { status: 405, headers: { Allow: 'GET, POST, DELETE' } })
  } catch (error) { return accessResponse(error) }
} }
