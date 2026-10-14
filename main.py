"""Daily official USD/KZT rate -> Telegram. Stdlib only, no AI API required."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html import escape
from zoneinfo import ZoneInfo
from datetime import datetime

NBRK_ENDPOINT = "https://nationalbank.kz/rss/get_rates.cfm"
TELEGRAM_ENDPOINT = "https://api.telegram.org"
TIME_ZONE = ZoneInfo("Asia/Almaty")
LOG = logging.getLogger("usd_kzt_bot")


@dataclass(frozen=True)
class Rate:
    for_date: date
    kzt_per_usd: Decimal


def _read_url(url: str, *, data: bytes | None = None, timeout: int = 20) -> bytes:
    """Fetch HTTPS data, retrying transient transport/server errors."""
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "USD-KZT-Telegram-Digest/1.0", "Accept": "application/xml,application/json,*/*"},
        method="POST" if data is not None else "GET",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            LOG.warning("Temporary HTTP error %s (%d/3)", exc.code, attempt + 1)
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == 2:
                raise
            LOG.warning("Temporary network error (%d/3): %s", attempt + 1, exc)
        time.sleep(2 ** attempt)
    raise RuntimeError("No response received")


def parse_rate(xml_bytes: bytes, for_date: date) -> Rate:
    """Parse NBRK RSS XML; the 'quant' field means KZT per N USD."""
    root = ET.fromstring(xml_bytes)
    for item in root.findall(".//item"):
        if (item.findtext("title") or "").strip().upper() != "USD":
            continue
        raw_amount = (item.findtext("description") or "").strip().replace(" ", "").replace(",", ".")
        raw_quant = (item.findtext("quant") or "1").strip().replace(",", ".")
        try:
            amount = Decimal(raw_amount)
            quant = Decimal(raw_quant)
            if not amount.is_finite() or not quant.is_finite() or amount <= 0 or quant <= 0:
                raise ValueError("Invalid currency quote")
            return Rate(for_date, amount / quant)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("NBRK USD quote is invalid") from exc
    raise ValueError("No USD quote in NBRK XML")


def get_rate(on_date: date) -> Rate:
    query = urllib.parse.urlencode({"fdate": on_date.strftime("%d.%m.%Y")})
    return parse_rate(_read_url(f"{NBRK_ENDPOINT}?{query}"), on_date)


def get_recent_rate(start_date: date, max_back_days: int = 7) -> Rate:
    """Use the requested date, or last available historical official rate."""
    last_error: Exception | None = None
    for day_back in range(max_back_days + 1):
        candidate = start_date - timedelta(days=day_back)
        try:
            return get_rate(candidate)
        except (ValueError, ET.ParseError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            LOG.warning("NBRK quote unavailable for %s (%s)", candidate.isoformat(), exc)
    raise RuntimeError("Official NBRK USD quote unavailable for the last 8 days") from last_error


def fmt_money(amount: Decimal, signed: bool = False) -> str:
    out = f"{abs(amount):,.2f}".replace(",", " ").replace(".", ",")
    prefix = "+" if amount > 0 and signed else "−" if amount < 0 and signed else ""
    return prefix + out


def make_message(today: Rate, previous: Rate | None) -> str:
    title = f"💵 <b>Курс доллара — {today.for_date:%d.%m.%Y}</b>"
    value = f"🇺🇸 1 USD = <b>{fmt_money(today.kzt_per_usd)} ₸</b>"
    parts = [title, value]
    if previous is not None:
        diff = today.kzt_per_usd - previous.kzt_per_usd
        if diff == 0:
            parts.append(f"➖ Без изменений к {previous.for_date:%d.%m.%Y}")
        else:
            icon = "📈" if diff > 0 else "📉"
            percent = (diff / previous.kzt_per_usd) * 100
            parts.append(
                f"{icon} К {previous.for_date:%d.%m.%Y}: "
                f"<b>{fmt_money(diff, signed=True)} ₸ ({fmt_money(percent, signed=True)}%)</b>"
            )
    parts.append("\n🏦 Источник: Национальный банк Казахстана")
    parts.append("<i>Это официальный курс, не курс покупки/продажи в обменниках.</i>")
    return "\n".join(parts)


def send_to_telegram(token: str, chat_id: str, message: str) -> None:
    # Secret only in the URL used locally; never print the URL or HTTP response.
    endpoint = f"{TELEGRAM_ENDPOINT}/bot{urllib.parse.quote(token, safe=':')}/sendMessage"
    data = json.dumps(
        {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    ).encode("utf-8")
    try:
        response = json.loads(_read_url(endpoint, data=data))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram API rejected request (HTTP {exc.code}); check your bot token and chat ID") from None
    if not response.get("ok"):
        raise RuntimeError("Telegram API reported a failed send; check your bot token and chat ID")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        LOG.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        return 2

    current_day = datetime.now(TIME_ZONE).date()
    if os.getenv("TEST_DATE"):
        current_day = date.fromisoformat(os.environ["TEST_DATE"])
    try:
        current = get_recent_rate(current_day)
        try:
            previous = get_recent_rate(current.for_date - timedelta(days=1))
        except RuntimeError:
            previous = None
        message = make_message(current, previous)
        send_to_telegram(token, chat_id, message)
        LOG.info("Telegram rate message sent. Official rate date: %s", current.for_date.isoformat())
        return 0
    except Exception:
        # Avoid printing HTTP request object/URL, which could leak the bot token.
        LOG.error("Could not deliver USD/KZT rate. Check API availability and credentials.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
