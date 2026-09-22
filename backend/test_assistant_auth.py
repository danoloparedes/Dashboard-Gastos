import io
import json
import os
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import assistant_auth as auth


class AuthTests(unittest.TestCase):
  def setUp(self):
    self.uri = 'file:auth_tests?mode=memory&cache=shared'
    self.keeper = sqlite3.connect(self.uri, uri=True)
    self.keeper.executescript('CREATE TABLE sessions (token TEXT PRIMARY KEY, version TEXT, expires REAL); CREATE TABLE limits (bucket TEXT PRIMARY KEY, hits INTEGER, expires REAL);')
    self.addCleanup(self.keeper.close)
    mock = patch.object(auth, 'connection', side_effect=lambda: sqlite3.connect(self.uri, uri=True))
    mock.start()
    self.addCleanup(mock.stop)
    env = patch.dict(os.environ, {'ASSISTANT_PASSWORD': 'test-password-123456', 'ASSISTANT_DAILY_OPENAI_LIMIT': '2'})
    env.start()
    self.addCleanup(env.stop)

  def handler(self, method='POST', password='test-password-123456', cookie=''):
    data = json.dumps({'password': password}).encode()
    handler = SimpleNamespace(command=method, headers={'Content-Length': str(len(data)), 'X-Gastos-Request': '1', 'Cookie': cookie},
                              client_address=('127.0.0.1', 1234), rfile=io.BytesIO(data), wfile=io.BytesIO(), response_headers={})
    handler.send_response = lambda value: setattr(handler, 'status', value)
    handler.send_header = lambda key, value: handler.response_headers.update({key: value})
    handler.end_headers = lambda: None
    return handler

  def test_login_session_and_revocation(self):
    login = self.handler()
    auth.handle_session(login)
    self.assertEqual(login.status, 200)
    cookie = login.response_headers['Set-Cookie'].split(';')[0]
    self.assertIn('Max-Age=34560000', login.response_headers['Set-Cookie'])
    authenticated = self.handler(cookie=cookie)
    auth.require_session(authenticated)
    with patch.object(auth.time, 'time', return_value=999999999999):
      self.assertTrue(auth.session(authenticated))
      resumed = self.handler('GET', cookie=cookie)
      auth.handle_session(resumed)
      self.assertEqual(resumed.response_headers['Set-Cookie'], login.response_headers['Set-Cookie'])
    logout = self.handler('DELETE', cookie=cookie)
    auth.handle_session(logout)
    self.assertFalse(auth.session(authenticated))

  def test_anonymous_and_cross_site_denied(self):
    with self.assertRaises(auth.AccessError):
      auth.require_session(self.handler())
    handler = self.handler()
    handler.headers['Sec-Fetch-Site'] = 'cross-site'
    auth.handle_session(handler)
    self.assertEqual(handler.status, 403)

  def test_failed_logins_are_limited(self):
    for _ in range(5):
      handler = self.handler(password='wrong')
      auth.handle_session(handler)
      self.assertEqual(handler.status, 401)
    handler = self.handler()
    auth.handle_session(handler)
    self.assertEqual(handler.status, 429)

  def test_quota_is_persistent_and_shared(self):
    auth.consume_openai()
    auth.consume_openai()
    with self.assertRaises(auth.AccessError) as error:
      auth.consume_openai()
    self.assertEqual(error.exception.status, 429)


if __name__ == '__main__':
  unittest.main()
