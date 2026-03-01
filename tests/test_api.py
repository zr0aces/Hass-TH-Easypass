"""Unit tests for custom_components/easypass/api.py.

All HTTP calls are mocked so no real network access is needed.
"""
import sys
import os
import types

# ---------------------------------------------------------------------------
# Stub the 'homeassistant' package so api.py (via its siblings) can be
# imported without a full HA installation.
# ---------------------------------------------------------------------------
ha_stub = types.ModuleType("homeassistant")
sys.modules.setdefault("homeassistant", ha_stub)
for _sub in (
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.helpers",
    "homeassistant.helpers.config_validation",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.typing",
    "homeassistant.const",
    "homeassistant.core",
):
    sys.modules.setdefault(_sub, types.ModuleType(_sub))

# Insert the repo root so relative imports inside the package resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, call
import pytest
from custom_components.easypass.api import (
    LoginEasyPass,
    EASYPASS_LOGIN_URL,
    EASYPASS_SIGNIN_URL,
    EASYPASS_URL,
    MIN_CONTENT_SIZE,
)

# ---------------------------------------------------------------------------
# HTML fixture that mimics the thaieasypass.com smartcard page
# ---------------------------------------------------------------------------
_ONE_CARD_HTML = """
<html><body>
<table>
  <tr class="head-table">
    <td>ทะเบียนรถ</td>
    <td>เลขสมาร์ทการ์ด (S/N)</td>
    <td>หมายเลข OBU</td>
    <td>จำนวนเงิน</td>
  </tr>
  <tr>
    <td>กข 1234</td>
    <td>SN00001</td>
    <td>OBU00001</td>
    <td>1,500.00</td>
  </tr>
</table>
</body></html>
"""

_TWO_CARD_HTML = """
<html><body>
<table>
  <tr class="head-table">
    <td>ทะเบียนรถ</td>
    <td>เลขสมาร์ทการ์ด (S/N)</td>
    <td>หมายเลข OBU</td>
    <td>จำนวนเงิน</td>
  </tr>
  <tr>
    <td>กข 1234</td>
    <td>SN00001</td>
    <td>OBU00001</td>
    <td>1,500.00</td>
  </tr>
  <tr>
    <td>คง 5678</td>
    <td>SN00002</td>
    <td>OBU00002</td>
    <td>2,000.50</td>
  </tr>
</table>
</body></html>
"""

_LOGIN_CREDS = {"username": "user@example.com", "password": "secret"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code=200, content=_ONE_CARD_HTML, headers=None):
    """Return a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    encoded = content.encode("utf-8")
    resp.content = encoded
    resp.headers = headers or {"Content-Length": str(len(encoded))}
    return resp


# ===========================================================================
# LoginEasyPass.login_easypass
# ===========================================================================

class TestLoginEasyPass:
    def test_login_visits_login_page_then_posts_signin(self):
        """login_easypass must GET the login page then POST credentials."""
        session = MagicMock()
        LoginEasyPass.login_easypass(session, _LOGIN_CREDS)

        session.get.assert_called_once_with(EASYPASS_LOGIN_URL)
        session.post.assert_called_once()
        post_call = session.post.call_args
        assert post_call[0][0] == EASYPASS_SIGNIN_URL
        assert "email=user%40example.com" in post_call[1]["data"] or \
               "email=user@example.com" in post_call[1]["data"]  # requests may or may not percent-encode @
        assert "secret" in post_call[1]["data"]

    def test_login_sends_referer_header(self):
        """Referer header must be the login page URL."""
        session = MagicMock()
        LoginEasyPass.login_easypass(session, _LOGIN_CREDS)

        headers = session.post.call_args[1]["headers"]
        assert headers["Referer"] == EASYPASS_LOGIN_URL

    def test_login_content_type_form_urlencoded(self):
        """Content-Type must be application/x-www-form-urlencoded."""
        session = MagicMock()
        LoginEasyPass.login_easypass(session, _LOGIN_CREDS)

        headers = session.post.call_args[1]["headers"]
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"


# ===========================================================================
# LoginEasyPass.get_response
# ===========================================================================

class TestGetResponse:
    def test_returns_response_on_200_with_enough_content(self):
        """Successful 200 response with large-enough body is returned."""
        session = MagicMock()
        large_content = "x" * (MIN_CONTENT_SIZE + 100)
        resp = _make_response(content=large_content)
        session.get.return_value = resp

        result = LoginEasyPass.get_response(session, EASYPASS_URL, _LOGIN_CREDS)

        assert result is resp

    def test_triggers_relogin_on_non_200(self):
        """Non-200 response must trigger re-login."""
        session = MagicMock()
        session.get.return_value = _make_response(status_code=302, content="")

        with patch.object(LoginEasyPass, "login_easypass") as mock_login:
            LoginEasyPass.get_response(session, EASYPASS_URL, _LOGIN_CREDS)
            mock_login.assert_called_once_with(session, _LOGIN_CREDS)

    def test_triggers_relogin_when_content_too_small(self):
        """200 response with body smaller than MIN_CONTENT_SIZE triggers re-login."""
        session = MagicMock()
        small_content = "x" * (MIN_CONTENT_SIZE - 1)
        session.get.return_value = _make_response(content=small_content)

        with patch.object(LoginEasyPass, "login_easypass") as mock_login:
            LoginEasyPass.get_response(session, EASYPASS_URL, _LOGIN_CREDS)
            mock_login.assert_called_once_with(session, _LOGIN_CREDS)

    def test_handles_missing_content_length_header(self):
        """Missing Content-Length header must not raise an exception."""
        session = MagicMock()
        large_content = "x" * (MIN_CONTENT_SIZE + 100)
        resp = _make_response(content=large_content, headers={})  # no Content-Length
        session.get.return_value = resp

        # Should not raise; fallback to len(response.content)
        result = LoginEasyPass.get_response(session, EASYPASS_URL, _LOGIN_CREDS)
        assert result is resp

    def test_handles_missing_keep_alive_header(self):
        """Missing Keep-Alive header must not raise an exception."""
        session = MagicMock()
        large_content = "x" * (MIN_CONTENT_SIZE + 100)
        resp = _make_response(content=large_content, headers={"Content-Length": str(len(large_content.encode()))})
        session.get.return_value = resp

        result = LoginEasyPass.get_response(session, EASYPASS_URL, _LOGIN_CREDS)
        assert result is resp

    def test_returns_none_on_exception(self):
        """Network exception must return None (not propagate)."""
        session = MagicMock()
        session.get.side_effect = ConnectionError("network down")

        with patch("time.sleep"):
            result = LoginEasyPass.get_response(session, EASYPASS_URL, _LOGIN_CREDS)

        assert result is None


# ===========================================================================
# LoginEasyPass.get_easypass
# ===========================================================================

class TestGetEasypass:
    def _session_returning(self, html):
        """Return a mock session and patch get_response to yield *html* content."""
        session = MagicMock()
        resp = _make_response(content=html)
        return session, resp

    def test_parses_single_card(self):
        """get_easypass returns a list with one card dict for a single-card page."""
        session, resp = self._session_returning(_ONE_CARD_HTML)

        with patch.object(LoginEasyPass, "get_response", return_value=resp):
            results = LoginEasyPass.get_easypass(session, _LOGIN_CREDS)

        assert isinstance(results, list)
        assert len(results) == 1
        card = results[0]
        assert card["ทะเบียนรถ"] == "กข 1234"
        assert card["เลขสมาร์ทการ์ด (S/N)"] == "SN00001"
        assert card["จำนวนเงิน"] == "1,500.00"

    def test_parses_two_cards(self):
        """get_easypass returns two card dicts for a two-card page."""
        session, resp = self._session_returning(_TWO_CARD_HTML)

        with patch.object(LoginEasyPass, "get_response", return_value=resp):
            results = LoginEasyPass.get_easypass(session, _LOGIN_CREDS)

        assert len(results) == 2
        assert results[0]["ทะเบียนรถ"] == "กข 1234"
        assert results[1]["ทะเบียนรถ"] == "คง 5678"
        assert results[1]["จำนวนเงิน"] == "2,000.50"

    def test_returns_login_failed_when_no_response(self):
        """If get_response returns None (session error), return 'Login Failed'."""
        session = MagicMock()

        with patch.object(LoginEasyPass, "get_response", return_value=None):
            result = LoginEasyPass.get_easypass(session, _LOGIN_CREDS)

        assert result == "Login Failed"

    def test_returns_login_failed_when_no_table(self):
        """Page with no <table> element returns 'Login Failed'."""
        session = MagicMock()
        html = "<html><body><p>No table here</p></body></html>"
        resp = _make_response(content=html)

        with patch.object(LoginEasyPass, "get_response", return_value=resp):
            result = LoginEasyPass.get_easypass(session, _LOGIN_CREDS)

        assert result == "Login Failed"
