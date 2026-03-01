import logging
import re
import time

import requests
from bs4 import BeautifulSoup

EASYPASS_LOGIN_URL = "https://www.thaieasypass.com/th/member/login"
EASYPASS_SIGNIN_URL = "https://www.thaieasypass.com/th/member/signin"
EASYPASS_URL = "https://www.thaieasypass.com/th/easypass/smartcard"

REFRESH_SEC = 120  # will be over writen if refresh in meta content is higher
MAX_CONNECTION = 50
MIN_CONTENT_SIZE = 2000  # for check if no data return even with status_code 200
MAX_CONNECTION_USED = MAX_CONNECTION - 1

_LOGGER = logging.getLogger("easypass_api")


TIMEZONE = "Asia/Bangkok"
DATETIME_FORMAT = "%Y/%m/%dT%H:%M:%S%z"  # ISO 8601
EASYPASS_RETRY_WAIT_SEC = 300


class LoginEasyPass:
    @staticmethod
    def login_easypass(session, login):
        session.get(EASYPASS_LOGIN_URL)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": EASYPASS_LOGIN_URL,
        }
        payload = f"email={login['username']}&password={login['password']}"
        session.post(EASYPASS_SIGNIN_URL, data=payload, headers=headers)

    @staticmethod
    def get_response(session, url, login, min_cont_size=MIN_CONTENT_SIZE):
        global REFRESH_SEC
        result = None
        try:
            response = session.get(url)
            content_length = int(
                response.headers.get("Content-Length", len(response.content))
            )
            if response.status_code != 200 or content_length < min_cont_size:
                if response.status_code != 200:
                    _LOGGER.warning("Response status is %s", response.status_code)
                LoginEasyPass.login_easypass(session, login)
            else:
                keep_alive = response.headers.get("Keep-Alive", "")
                match = re.search(r"timeout=(\d+)", keep_alive)
                if match:
                    timeout = int(match[1])
                    match = re.search(r"max=(\d+)", keep_alive)
                    if match:
                        connection_left = int(match[1])
                        if connection_left < MAX_CONNECTION_USED:
                            time.sleep(timeout * 2)
                match = re.search(
                    r"refresh.*\b(\d+)\b", response.content.decode("UTF-8")
                )
                if match:
                    refresh = int(match[1])
                    if refresh > REFRESH_SEC:
                        REFRESH_SEC = refresh
                result = response
        except Exception as err:
            _LOGGER.error("Error fetching data from %s: %s", url, err)
            time.sleep(EASYPASS_RETRY_WAIT_SEC)
        return result

    @staticmethod
    def get_easypass(session, login):
        results = []
        response = LoginEasyPass.get_response(session, EASYPASS_URL, login)
        if not response:
            _LOGGER.warning("Failed to retrieve response from %s", EASYPASS_URL)
            return "Login Failed"
        try:
            soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
            table = soup.find("table")
            headers = [
                header.text.strip()
                for header in table.find("tr", class_="head-table").find_all("td")
            ]
            for row in table.find_all("tr"):
                if "head-table" in row.get("class", []):
                    continue
                row_dict = {
                    headers[i]: cell.text.strip()
                    for i, cell in enumerate(row.find_all("td"))
                }
                results.append(row_dict)
            _LOGGER.info(results)
            return results
        except Exception as err:
            _LOGGER.error("Failed to parse Easy Pass data: %s", err)
            return "Login Failed"
