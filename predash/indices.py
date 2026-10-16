"""Latest KOSPI/KOSDAQ index snapshots for the investment dashboard.

Yahoo Finance chart data is used for a lightweight, keyless quote lookup.
Values are never fabricated: failures are surfaced to the UI, and the
source timestamp is returned so the dashboard can distinguish stale quotes.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

import requests


SEOUL = ZoneInfo("Asia/Seoul")
INDEXES = (("코스피", "^KS11"), ("코스닥", "^KQ11"))


class IndexQuoteError(RuntimeError):
    """Raised when the quote provider cannot return a valid index snapshot."""


def _fetch_one(name, symbol):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + quote(symbol, safe="")
    try:
        response = requests.get(
            url,
            params={"range": "5d", "interval": "1d", "includePrePost": "false"},
            headers={"User-Agent": "Mozilla/5.0 PreDash/1.0"},
            timeout=(5, 12),
        )
        response.raise_for_status()
        payload = response.json()
        chart = payload.get("chart") or {}
        if chart.get("error"):
            raise ValueError
        result = (chart.get("result") or [])[0]
        meta = result.get("meta") or {}
        quote_rows = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quote_rows.get("close") or []
        valid_closes = [float(value) for value in closes if value is not None and float(value) > 0]
        if not valid_closes:
            raise ValueError

        current = meta.get("regularMarketPrice")
        if current is None or float(current) <= 0:
            current = valid_closes[-1]
        current = float(current)

        # With a multi-day daily chart, the penultimate close is the
        # previous trading session even when today is still in progress.
        previous = valid_closes[-2] if len(valid_closes) >= 2 else None
        if previous is None or float(previous) <= 0:
            raise ValueError
        previous = float(previous)

        timestamp = meta.get("regularMarketTime")
        if timestamp:
            quote_time = datetime.fromtimestamp(int(timestamp), tz=SEOUL)
        else:
            timestamps = result.get("timestamp") or []
            quote_time = datetime.fromtimestamp(int(timestamps[-1]), tz=SEOUL) if timestamps else datetime.now(SEOUL)

        change = current - previous
        return {
            "name": name,
            "value": current,
            "previous": previous,
            "change": change,
            "change_pct": change / previous * 100,
            "date": quote_time.strftime("%Y-%m-%d"),
            "time": quote_time.strftime("%H:%M"),
            "timestamp": quote_time.isoformat(),
            "status": "상승" if change > 0 else "하락" if change < 0 else "보합",
            "source": "Yahoo Finance",
        }
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, ZeroDivisionError):
        raise IndexQuoteError(f"{name} 지수 시세를 가져오지 못했습니다.") from None


def fetch_indices():
    """Return both index snapshots or raise a safe, source-neutral error."""
    rows = []
    errors = []
    for name, symbol in INDEXES:
        try:
            rows.append(_fetch_one(name, symbol))
        except IndexQuoteError as exc:
            errors.append(str(exc))
    if len(rows) != len(INDEXES):
        raise IndexQuoteError("코스피·코스닥 시세 연결에 실패했습니다. 잠시 후 새로고침하세요.")
    return rows
