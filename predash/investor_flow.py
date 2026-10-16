"""KOSPI/KOSDAQ investor trading value, aggregated by domestic vs foreign investors.

Uses pykrx to read investor-flow statistics published through the KRX Data
Marketplace. These are daily market-wide trading values, not account-specific
transactions and not a guaranteed real-time feed.
"""
from datetime import date, timedelta


class InvestorFlowError(RuntimeError):
    """Raised when market-wide investor trading data cannot be validated."""


MARKETS = (("코스피", "KOSPI"), ("코스닥", "KOSDAQ"))


def _as_int(row, candidates):
    for key in candidates:
        if key in row.index:
            value = row[key]
            if value is not None:
                try:
                    return int(float(value))
                except (TypeError, ValueError, OverflowError):
                    continue
    raise InvestorFlowError("투자자별 거래대금 데이터의 항목 구성이 예상과 다릅니다.")


def _domestic_total(row):
    # Domestic aggregate = individuals + institutions + other domestic corporations.
    return sum(
        _as_int(row, names)
        for names in (
            ("개인",),
            ("기관합계", "기관"),
            ("기타법인",),
        )
    )


def _foreign_total(row):
    return _as_int(row, ("외국인합계", "외국인"))


def _fetch_market(label, market, start, end):
    try:
        from pykrx import stock

        sell = stock.get_market_trading_value_by_date(start, end, market, on="매도")
        buy = stock.get_market_trading_value_by_date(start, end, market, on="매수")
        if sell is None or buy is None or sell.empty or buy.empty:
            raise InvestorFlowError(f"{label} 투자자별 거래대금 자료가 없습니다.")

        sell.index = __import__("pandas").to_datetime(sell.index, errors="coerce")
        buy.index = __import__("pandas").to_datetime(buy.index, errors="coerce")
        sell = sell.loc[~sell.index.isna()]
        buy = buy.loc[~buy.index.isna()]
        common = sorted(set(sell.index).intersection(set(buy.index)))
        if not common:
            raise InvestorFlowError(f"{label} 매수·매도 자료의 공통 거래일을 찾지 못했습니다.")

        latest = common[-1]
        sell_row = sell.loc[latest]
        buy_row = buy.loc[latest]
        # Duplicate index rows are not expected; refuse ambiguous records.
        if getattr(sell_row, "ndim", 1) != 1 or getattr(buy_row, "ndim", 1) != 1:
            raise InvestorFlowError(f"{label} 거래일 데이터가 중복되어 표시를 보류합니다.")

        domestic_sell = _domestic_total(sell_row)
        domestic_buy = _domestic_total(buy_row)
        foreign_sell = _foreign_total(sell_row)
        foreign_buy = _foreign_total(buy_row)
        return {
            "market": label,
            "date": latest.strftime("%Y-%m-%d"),
            "domestic_sell": domestic_sell,
            "domestic_buy": domestic_buy,
            "domestic_net": domestic_buy - domestic_sell,
            "foreign_sell": foreign_sell,
            "foreign_buy": foreign_buy,
            "foreign_net": foreign_buy - foreign_sell,
        }
    except InvestorFlowError:
        raise
    except Exception:
        # Keep provider internals and response payloads out of the public UI.
        raise InvestorFlowError(
            f"{label} 투자자별 매매동향을 조회하지 못했습니다. 잠시 후 다시 시도하세요."
        ) from None


def fetch_investor_flow(asof=None, lookback_days=12):
    """Return the latest common valid daily record for both domestic and foreign flows."""
    asof = asof or date.today()
    start = (asof - timedelta(days=lookback_days)).strftime("%Y%m%d")
    end = asof.strftime("%Y%m%d")
    rows = [_fetch_market(label, market, start, end) for label, market in MARKETS]
    if len({row["date"] for row in rows}) != 1:
        # The dashboard should not compare different dates as if they were simultaneous.
        latest_date = min(row["date"] for row in rows)
        rows = [row for row in rows if row["date"] == latest_date]
        if len(rows) != 2:
            raise InvestorFlowError("코스피·코스닥의 공통 기준일을 찾지 못했습니다.")
    return rows
