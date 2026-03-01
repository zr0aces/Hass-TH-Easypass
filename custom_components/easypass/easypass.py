import logging

import requests

from .api import LoginEasyPass

_LOGGER = logging.getLogger("easypass")


class EasyPassInstance:
    def __init__(self, value: str) -> None:
        self._sensor = value
        self._attr_native_value = None

    @property
    def value(self):
        self._offset = self._sensor["offset"]
        self._offset = int(self._offset) - 1
        with requests.session() as session:
            LoginEasyPass.login_easypass(session, self._sensor)
            cards = LoginEasyPass.get_easypass(session, self._sensor)
            if cards == "Login Failed":
                return cards, ""
            else:
                try:
                    attr = {
                        "ทะเบียนรถ": cards[self._offset]["ทะเบียนรถ"],
                        "เลขสมาร์ทการ์ด": cards[self._offset]["เลขสมาร์ทการ์ด (S/N)"],
                    }
                    balance_value = cards[self._offset]["จำนวนเงิน"]
                    balance_value = balance_value.replace(",", "")
                    return balance_value, attr
                except (IndexError, KeyError) as err:
                    _LOGGER.warning(
                        "Offset %s out of range, falling back to first card: %s",
                        self._sensor["offset"],
                        err,
                    )
                    length = len(cards)
                    balance_value = cards[0]["จำนวนเงิน"]
                    balance_value = balance_value.replace(",", "")
                    attr = {
                        "license_plate": cards[0]["ทะเบียนรถ"],
                        "balance": balance_value,
                        "smartcard": cards[0]["เลขสมาร์ทการ์ด (S/N)"],
                    }
                    return balance_value, attr
