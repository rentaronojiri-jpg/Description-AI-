# -*- coding: utf-8 -*-
"""
株予測ツール Web版（ローカルサーバー）
ブラウザからの分析リクエストのたびにyfinanceへ問い合わせ、常に最新（ライブ）の
データで売買シグナル・簡易予測を計算して返す。キャッシュはしない。

起動:
    py webapp/server.py
    → http://127.0.0.1:8765 をブラウザで開く（起動batが自動で開く）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, request, send_from_directory

from analysis_core import (
    analyze,
    currency_symbol,
    format_marketcap,
    get_dividend_yield_pct,
    get_roe_pct,
    resolve_query_auto,
    search_quotes,
)

app = Flask(__name__, static_folder="static", static_url_path="")


@app.after_request
def add_no_cache_headers(resp):
    # 常に最新データを返すツールのため、ブラウザ側のキャッシュも無効化する
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/search")
def api_search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"candidates": []})
    candidates = search_quotes(query, max_results=8)
    return jsonify({
        "candidates": [
            {
                "symbol": c.get("symbol"),
                "name": c.get("shortname") or c.get("longname") or c.get("symbol"),
                "exchange": c.get("exchDisp", ""),
            }
            for c in candidates
        ]
    })


def pd_isna(v):
    if v is None:
        return True
    return v != v  # NaN != NaN, works without importing pandas here


def _series_points(index, values):
    points = []
    for ts, v in zip(index, values):
        if pd_isna(v):
            continue
        points.append({"time": ts.strftime("%Y-%m-%d"), "value": round(float(v), 4)})
    return points


def build_chart_payload(hist, tail_days: int = 220):
    d = hist.tail(tail_days)
    candles, volume = [], []
    for ts, row in d.iterrows():
        t = ts.strftime("%Y-%m-%d")
        candles.append({
            "time": t,
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
        })
        up = row["Close"] >= row["Open"]
        volume.append({
            "time": t,
            "value": float(row["Volume"]),
            "color": "rgba(12,163,12,0.55)" if up else "rgba(208,59,59,0.55)",
        })

    macd_hist = []
    for ts, v in d["MACD_hist"].items():
        if pd_isna(v):
            continue
        macd_hist.append({
            "time": ts.strftime("%Y-%m-%d"),
            "value": round(float(v), 4),
            "color": "rgba(12,163,12,0.7)" if v >= 0 else "rgba(208,59,59,0.7)",
        })

    return {
        "candles": candles,
        "volume": volume,
        "sma5": _series_points(d.index, d["SMA5"]),
        "sma25": _series_points(d.index, d["SMA25"]),
        "sma75": _series_points(d.index, d["SMA75"]),
        "rsi": _series_points(d.index, d["RSI14"]),
        "macd": _series_points(d.index, d["MACD"]),
        "macd_signal": _series_points(d.index, d["MACD_signal"]),
        "macd_hist": macd_hist,
    }


@app.route("/api/analyze")
def api_analyze():
    query = (request.args.get("q") or "").strip()
    forecast_days = request.args.get("forecast_days", default=10, type=int)
    tech_weight = request.args.get("tech_weight", default=0.55, type=float)

    if not query:
        return jsonify({"error": "銘柄を入力してください。"}), 400

    symbol, candidates = resolve_query_auto(query)
    if not symbol:
        return jsonify({
            "error": f"'{query}' に一致する銘柄が見つかりませんでした。会社名は英語表記、または証券コードでお試しください。",
        }), 404

    try:
        result = analyze(symbol, forecast_days=forecast_days, tech_weight=tech_weight)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    hist = result["hist"]
    info = result["info"]
    tech = result["tech"]
    fund = result["fund"]
    combined = result["combined"]
    forecast = result["forecast"]
    live_price = result["live_price"]
    prev_close = result["prev_close"]
    change = live_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0

    forecast_line = [{"time": hist.index[-1].strftime("%Y-%m-%d"), "value": round(float(live_price), 4)}]
    forecast_line += _series_points(forecast["series"].index, forecast["series"].values)

    payload = {
        "symbol": result["ticker_symbol"],
        "name": result["name"],
        "currency": (info.get("currency") or "JPY"),
        "currency_symbol": currency_symbol(info),
        "live_price": round(float(live_price), 4),
        "prev_close": round(float(prev_close), 4),
        "change": round(float(change), 4),
        "change_pct": round(float(change_pct), 3),
        "updated_at": hist.index[-1].strftime("%Y-%m-%d"),
        "tech": tech,
        "fund": fund,
        "combined": combined,
        "forecast": {
            "trend": forecast["trend"],
            "change_pct": round(float(forecast["change_pct"]), 2),
            "lookback_days": forecast["lookback_days"],
            "forecast_days": forecast_days,
            "line": forecast_line,
        },
        "metrics": {
            "per": info.get("trailingPE"),
            "pbr": info.get("priceToBook"),
            "dividend_yield_pct": get_dividend_yield_pct(info),
            "roe_pct": get_roe_pct(info),
            "market_cap_fmt": format_marketcap(info.get("marketCap"), info),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
            "rsi": round(float(hist["RSI14"].iloc[-1]), 1) if len(hist) else None,
            "volume": int(hist["Volume"].iloc[-1]) if len(hist) else None,
        },
        "chart": build_chart_payload(hist),
        "alt_candidates": [
            {"symbol": c.get("symbol"), "name": c.get("shortname") or c.get("longname"), "exchange": c.get("exchDisp", "")}
            for c in candidates[:5]
        ] if candidates else [],
    }
    return jsonify(payload)


if __name__ == "__main__":
    print("=" * 60)
    print(" 株予測ツール Web版を起動しました")
    print(" ブラウザで http://127.0.0.1:8765 を開いてください")
    print(" 終了するにはこのウィンドウで Ctrl+C を押してください")
    print("=" * 60)
    app.run(host="127.0.0.1", port=8765, debug=False)
