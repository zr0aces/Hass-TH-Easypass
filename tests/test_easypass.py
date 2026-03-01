"""Unit tests for custom_components/easypass/easypass.py.

LoginEasyPass is mocked so no real network access is needed.
"""
import sys
import os
import types

# ---------------------------------------------------------------------------
# Stub 'homeassistant' package so the component can be imported standalone.
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock
from custom_components.easypass.easypass import EasyPassInstance

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------
_CARDS_ONE = [
    {
        "ทะเบียนรถ": "กข 1234",
        "เลขสมาร์ทการ์ด (S/N)": "SN00001",
        "หมายเลข OBU": "OBU00001",
        "จำนวนเงิน": "1,500.00",
    }
]

_CARDS_TWO = [
    {
        "ทะเบียนรถ": "กข 1234",
        "เลขสมาร์ทการ์ด (S/N)": "SN00001",
        "หมายเลข OBU": "OBU00001",
        "จำนวนเงิน": "1,500.00",
    },
    {
        "ทะเบียนรถ": "คง 5678",
        "เลขสมาร์ทการ์ด (S/N)": "SN00002",
        "หมายเลข OBU": "OBU00002",
        "จำนวนเงิน": "2,000.50",
    },
]


def _make_sensor(offset="1"):
    return {
        "name": "easypass_balance",
        "offset": offset,
        "username": "user@example.com",
        "password": "secret",
    }


# ===========================================================================
# EasyPassInstance.value — happy path
# ===========================================================================

class TestEasyPassInstanceValue:
    def _run(self, cards, offset="1"):
        sensor = _make_sensor(offset)
        instance = EasyPassInstance(sensor)
        with patch(
            "custom_components.easypass.easypass.LoginEasyPass.login_easypass"
        ) as mock_login, patch(
            "custom_components.easypass.easypass.LoginEasyPass.get_easypass",
            return_value=cards,
        ) as mock_get, patch(
            "custom_components.easypass.easypass.requests.session"
        ) as mock_session_ctx:
            mock_session_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
            return instance.value

    def test_single_card_offset_1_returns_balance(self):
        """offset=1 with one card → returns balance string and attr dict."""
        balance, attr = self._run(_CARDS_ONE, offset="1")
        assert balance == "1500.00"
        assert attr["ทะเบียนรถ"] == "กข 1234"
        assert attr["เลขสมาร์ทการ์ด"] == "SN00001"

    def test_balance_strips_comma(self):
        """Commas in the balance string must be removed."""
        balance, _ = self._run(_CARDS_ONE, offset="1")
        assert "," not in balance

    def test_second_card_offset_2_returns_correct_card(self):
        """offset=2 with two cards returns the second card."""
        balance, attr = self._run(_CARDS_TWO, offset="2")
        assert balance == "2000.50"
        assert attr["ทะเบียนรถ"] == "คง 5678"

    def test_login_failed_propagates(self):
        """If get_easypass returns 'Login Failed', value returns that string."""
        sensor = _make_sensor()
        instance = EasyPassInstance(sensor)
        with patch(
            "custom_components.easypass.easypass.LoginEasyPass.login_easypass"
        ), patch(
            "custom_components.easypass.easypass.LoginEasyPass.get_easypass",
            return_value="Login Failed",
        ), patch(
            "custom_components.easypass.easypass.requests.session"
        ) as mock_session_ctx:
            mock_session_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result, extra = instance.value
        assert result == "Login Failed"
        assert extra == ""

    def test_offset_out_of_range_falls_back_to_first_card(self):
        """offset beyond available cards falls back to the first card."""
        balance, attr = self._run(_CARDS_ONE, offset="5")
        # falls back to first card
        assert balance == "1500.00"
        assert attr["license_plate"] == "กข 1234"
        assert attr["smartcard"] == "SN00001"

    def test_two_cards_offset_1_returns_first(self):
        """With two cards, offset=1 returns the first card."""
        balance, attr = self._run(_CARDS_TWO, offset="1")
        assert balance == "1500.00"
        assert attr["ทะเบียนรถ"] == "กข 1234"

    def test_attr_contains_license_plate_and_smartcard_on_fallback(self):
        """Fallback path (offset out of range) uses English keys in attr dict."""
        balance, attr = self._run(_CARDS_ONE, offset="99")
        # The fallback branch uses English keys, unlike the normal path (Thai keys).
        assert "license_plate" in attr
        assert "balance" in attr
        assert "smartcard" in attr
