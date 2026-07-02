\
# -*- coding: utf-8 -*-
"""
株予測ツール
ファンダメンタルズ分析とテクニカル分析を組み合わせ、日本株の売買シグナルと
簡易的な株価トレンド予測を行う。

使い方:
    py stock_predictor.py                    # 対話モード（銘柄コード・会社名を入力して分析）
    py stock_predictor.py 7203
    py stock_predictor.py 7203 9984 6758 --forecast-days 15
    py stock_predictor.py 7203 --tech-weight 0.7
    py stock_predictor.py "Toyota"            # 会社名（英語表記）でも検索可能

出力:
    - コンソールにサマリーレポートを表示
    - output/ 以下に自己完結型HTMLダッシュボードを生成
"""

import argparse
import base64
import io
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import mplfinance as mpf
import numpy as np
import pandas as pd
import yfinance as yf

try:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OUTPUT_DIR = Path(__file__).parent / "output"

# Windows日本語フォント（文字化け防止）
for _font in ("Yu Gothic", "Meiryo", "MS Gothic"):
    if _font in {f.name for f in fm.fontManager.ttflist}:
        plt.rcParams["font.family"] = _font
        break
plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------

def normalize_ticker(code: str) -> str:
    """4桁数字のみなら日本株として .T を付与する"""
    code = code.strip().upper()
    if code.isdigit() and "." not in code:
        return f"{code}.T"
    return code


def search_and_select(query: str):
    """会社名などのあいまいな入力から候補を検索し、対話的に選択させてティッカーを返す"""
    try:
        results = yf.Search(query, max_results=8).quotes
    except Exception as e:
        print(f"[検索エラー] '{query}' の検索に失敗しました: {e}")
        return None

    results = [r for r in results if r.get("symbol") and r.get("quoteType") == "EQUITY"]
    if not results:
        print(
            f"'{query}' に一致する銘柄が見つかりませんでした。"
            " 会社名は英語表記（例: Toyota, SoftBank）か、証券コード（例: 7203）でお試しください。"
        )
        return None

    if len(results) == 1:
        chosen = results[0]
    else:
        print(f"\n'{query}' の検索結果:")
        for i, r in enumerate(results, 1):
            display_name = r.get("shortname") or r.get("longname") or ""
            print(f"  {i}. {r.get('symbol'):<10} {display_name}  ({r.get('exchDisp', '')})")
        sel = input("番号を選択してください（Enterで1番目）: ").strip()
        if not sel:
            chosen = results[0]
        else:
            try:
                chosen = results[int(sel) - 1]
            except (ValueError, IndexError):
                print("無効な選択のため1番目を使用します。")
                chosen = results[0]

    symbol = chosen.get("symbol")
    display_name = chosen.get("shortname") or chosen.get("longname") or symbol
    print(f"→ {symbol}（{display_name}）を使用します。")
    return symbol


def resolve_query(query: str):
    """入力文字列（証券コード／ティッカー／会社名）から実際のティッカーシンボルを解決する"""
    query = query.strip().lstrip("﻿")
    if not query:
        return None
    compact = query.replace(".", "")
    if compact.isdigit():
        return normalize_ticker(query)
    # 短い英字のみ（例: AAPL, TM）はティッカーとしてそのまま扱う
    if query.replace(".", "").isalpha() and len(query) <= 6 and " " not in query:
        return query.upper()
    # それ以外は会社名として検索
    return search_and_select(query)


def fetch_data(code: str, period: str = "1y"):
    ticker_symbol = normalize_ticker(code)
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period=period, auto_adjust=False)
    if hist.empty:
        raise ValueError(f"銘柄コード '{code}' のデータが取得できませんでした。コードを確認してください。")
    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}
    return ticker_symbol, hist, info


# ---------------------------------------------------------------------------
# テクニカル指標
# ---------------------------------------------------------------------------

def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"]

    df["SMA5"] = close.rolling(5).mean()
    df["SMA25"] = close.rolling(25).mean()
    df["SMA75"] = close.rolling(75).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI14"] = 100 - (100 / (1 + rs))
    df["RSI14"] = df["RSI14"].fillna(50)

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["BB_mid"] = bb_mid
    df["BB_upper"] = bb_mid + 2 * bb_std
    df["BB_lower"] = bb_mid - 2 * bb_std

    df["Volume_MA20"] = df["Volume"].rolling(20).mean()

    return df


# ---------------------------------------------------------------------------
# スコアリング
# ---------------------------------------------------------------------------

def technical_score(df: pd.DataFrame) -> dict:
    reasons = []
    score = 0
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    # トレンド（移動平均の並び）
    if pd.notna(last["SMA25"]) and pd.notna(last["SMA75"]):
        if last["Close"] > last["SMA25"] > last["SMA75"]:
            score += 20
            reasons.append("株価が短期・長期移動平均線の上にあり上昇トレンド（+20）")
        elif last["Close"] < last["SMA25"] < last["SMA75"]:
            score -= 20
            reasons.append("株価が短期・長期移動平均線の下にあり下降トレンド（-20）")

    # ゴールデンクロス／デッドクロス（SMA25とSMA75）
    if pd.notna(prev["SMA25"]) and pd.notna(prev["SMA75"]) and pd.notna(last["SMA25"]) and pd.notna(last["SMA75"]):
        if prev["SMA25"] <= prev["SMA75"] and last["SMA25"] > last["SMA75"]:
            score += 15
            reasons.append("直近でゴールデンクロス発生（+15）")
        elif prev["SMA25"] >= prev["SMA75"] and last["SMA25"] < last["SMA75"]:
            score -= 15
            reasons.append("直近でデッドクロス発生（-15）")

    # MACD
    if pd.notna(last["MACD"]) and pd.notna(last["MACD_signal"]):
        if last["MACD"] > last["MACD_signal"]:
            score += 15
            reasons.append("MACDがシグナルを上回り強気（+15）")
        else:
            score -= 15
            reasons.append("MACDがシグナルを下回り弱気（-15）")

    # RSI
    rsi = last["RSI14"]
    if pd.notna(rsi):
        if rsi < 30:
            score += 10
            reasons.append(f"RSIが{rsi:.1f}で売られすぎ、反発の可能性（+10）")
        elif rsi > 70:
            score -= 10
            reasons.append(f"RSIが{rsi:.1f}で買われすぎ、反落に警戒（-10）")

    # ボリンジャーバンド
    if pd.notna(last["BB_lower"]) and pd.notna(last["BB_upper"]):
        band_width = last["BB_upper"] - last["BB_lower"]
        if band_width > 0:
            if last["Close"] <= last["BB_lower"] + band_width * 0.1:
                score += 10
                reasons.append("株価がボリンジャーバンド下限付近で割安（+10）")
            elif last["Close"] >= last["BB_upper"] - band_width * 0.1:
                score -= 10
                reasons.append("株価がボリンジャーバンド上限付近で過熱（-10）")

    # 出来高
    if pd.notna(last["Volume_MA20"]) and last["Volume_MA20"] > 0:
        vol_ratio = last["Volume"] / last["Volume_MA20"]
        if vol_ratio > 1.5 and last["Close"] > prev["Close"]:
            score += 5
            reasons.append(f"出来高が20日平均の{vol_ratio:.1f}倍で上昇の勢いあり（+5）")

    score = max(-100, min(100, score))
    return {"score": score, "reasons": reasons}


def get_dividend_yield_pct(info: dict):
    """配当利回りを%単位で返す。dividendYieldはyfinanceのバージョンにより
    比率(0.037)と%表記(3.67)のどちらで返るか揺れるため、より安定した
    trailingAnnualDividendYield（常に比率）を優先的に使用する。"""
    ratio = info.get("trailingAnnualDividendYield")
    if ratio is not None:
        return ratio * 100
    raw = info.get("dividendYield")
    if raw is None:
        return None
    return raw if raw > 1 else raw * 100


def get_roe_pct(info: dict):
    """自己資本利益率(ROE)を%単位で返す。returnOnEquityは常に比率で
    返るため一律で100倍する（好業績企業ではROEが100%を超えることもある）。"""
    roe = info.get("returnOnEquity")
    if roe is None:
        return None
    return roe * 100


def fundamental_score(info: dict) -> dict:
    reasons = []
    score = 0

    per = info.get("trailingPE")
    if per is not None:
        if per < 0:
            score -= 20
            reasons.append(f"PERがマイナス（赤字）で割高感（-20）")
        elif per < 15:
            score += 20
            reasons.append(f"PER {per:.1f}倍で割安水準（+20）")
        elif per <= 25:
            reasons.append(f"PER {per:.1f}倍で標準的な水準（±0）")
        else:
            score -= 20
            reasons.append(f"PER {per:.1f}倍で割高水準（-20）")

    pbr = info.get("priceToBook")
    if pbr is not None:
        if pbr < 1:
            score += 15
            reasons.append(f"PBR {pbr:.2f}倍で解散価値割れ、割安（+15）")
        elif pbr <= 2:
            reasons.append(f"PBR {pbr:.2f}倍で標準的な水準（±0）")
        else:
            score -= 15
            reasons.append(f"PBR {pbr:.2f}倍で割高水準（-15）")

    dy_pct = get_dividend_yield_pct(info)
    if dy_pct is not None:
        if dy_pct >= 3:
            score += 15
            reasons.append(f"配当利回り{dy_pct:.2f}%で高配当（+15）")
        elif dy_pct >= 1:
            score += 5
            reasons.append(f"配当利回り{dy_pct:.2f}%（+5）")

    roe_pct = get_roe_pct(info)
    if roe_pct is not None:
        if roe_pct >= 10:
            score += 15
            reasons.append(f"ROE {roe_pct:.1f}%で高い資本効率（+15）")
        elif roe_pct >= 5:
            score += 5
            reasons.append(f"ROE {roe_pct:.1f}%（+5）")
        else:
            score -= 10
            reasons.append(f"ROE {roe_pct:.1f}%で資本効率が低い（-10）")

    score = max(-100, min(100, score))
    return {"score": score, "reasons": reasons}


def combined_signal(tech: dict, fund: dict, tech_weight: float = 0.55) -> dict:
    fund_weight = 1 - tech_weight
    total = tech["score"] * tech_weight + fund["score"] * fund_weight
    total = round(total)

    if total >= 50:
        label = "強い買い"
    elif total >= 20:
        label = "買い"
    elif total > -20:
        label = "中立"
    elif total > -50:
        label = "売り"
    else:
        label = "強い売り"

    return {"score": total, "label": label, "tech_weight": tech_weight, "fund_weight": fund_weight}


# ---------------------------------------------------------------------------
# 簡易トレンド予測
# ---------------------------------------------------------------------------

def simple_forecast(df: pd.DataFrame, forecast_days: int = 10, lookback_days: int = 60):
    recent = df["Close"].tail(lookback_days).dropna()
    x = np.arange(len(recent))
    y = recent.values
    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(recent), len(recent) + forecast_days)
    future_y = slope * future_x + intercept

    last_date = recent.index[-1]
    future_dates = pd.bdate_range(start=last_date, periods=forecast_days + 1)[1:]

    forecast_series = pd.Series(future_y, index=future_dates)

    last_price = recent.iloc[-1]
    change_pct = (future_y[-1] - last_price) / last_price * 100
    trend = "上昇" if slope > 0 else ("下降" if slope < 0 else "横ばい")

    return {
        "series": forecast_series,
        "slope": slope,
        "trend": trend,
        "change_pct": change_pct,
        "lookback_days": lookback_days,
    }


# ---------------------------------------------------------------------------
# チャート生成（base64埋め込み用）
# ---------------------------------------------------------------------------

def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def make_candle_chart(df: pd.DataFrame, name: str) -> str:
    plot_df = df.tail(180).copy()
    add_plots = [
        mpf.make_addplot(plot_df["RSI14"], panel=2, color="purple", ylabel="RSI"),
        mpf.make_addplot([70] * len(plot_df), panel=2, color="red", linestyle="--", width=0.7),
        mpf.make_addplot([30] * len(plot_df), panel=2, color="blue", linestyle="--", width=0.7),
        mpf.make_addplot(plot_df["MACD"], panel=3, color="orange", ylabel="MACD"),
        mpf.make_addplot(plot_df["MACD_signal"], panel=3, color="brown"),
        mpf.make_addplot(plot_df["MACD_hist"], panel=3, type="bar", color="grey", alpha=0.5),
    ]
    mc = mpf.make_marketcolors(up="red", down="green", inherit=True)
    style = mpf.make_mpf_style(base_mpf_style="yahoo", marketcolors=mc, rc={"font.family": plt.rcParams["font.family"]})

    fig, _ = mpf.plot(
        plot_df,
        type="candle",
        mav=(5, 25, 75),
        volume=True,
        addplot=add_plots,
        style=style,
        panel_ratios=(6, 2, 2, 2),
        figsize=(11, 10),
        returnfig=True,
        title=f"\n{name} 価格・出来高・RSI・MACD",
    )
    return fig_to_base64(fig)


def make_forecast_chart(df: pd.DataFrame, forecast: dict, name: str) -> str:
    fig, ax = plt.subplots(figsize=(11, 4.5))
    hist_tail = df["Close"].tail(forecast["lookback_days"])
    ax.plot(hist_tail.index, hist_tail.values, label="実績株価", color="black")
    ax.plot(forecast["series"].index, forecast["series"].values, label="トレンド予測（参考値）",
            color="red", linestyle="--", marker="o", markersize=3)
    ax.set_title(f"{name} 簡易トレンド予測（過去{forecast['lookback_days']}日の線形トレンドを延長）")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    return fig_to_base64(fig)


# ---------------------------------------------------------------------------
# HTMLレポート生成
# ---------------------------------------------------------------------------

def score_bar_html(score: int) -> str:
    pos = (score + 100) / 200 * 100
    color = "#c0392b" if score <= -20 else ("#7f8c8d" if score < 20 else "#1e8449")
    return (
        f'<div class="score-track"><div class="score-marker" '
        f'style="left:{pos:.1f}%; background:{color};"></div></div>'
        f'<div class="score-labels"><span>売り -100</span><span>中立 0</span><span>買い +100</span></div>'
    )


def build_html_report(ticker_symbol, name, hist, info, tech, fund, combined, forecast, candle_img, forecast_img) -> str:
    last = hist.iloc[-1]
    last_close = last["Close"]
    prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else last_close
    change = last_close - prev_close
    change_pct = change / prev_close * 100 if prev_close else 0
    change_color = "#c0392b" if change > 0 else ("#1e8449" if change < 0 else "#333")
    sym = currency_symbol(info)

    tech_reasons = "".join(f"<li>{r}</li>" for r in tech["reasons"]) or "<li>該当する指標なし</li>"
    fund_reasons = "".join(f"<li>{r}</li>" for r in fund["reasons"]) or "<li>ファンダメンタルズ情報が取得できませんでした</li>"

    generated_at = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    html = f"""
<meta charset="utf-8">
<title>{name}（{ticker_symbol}） 株価分析レポート</title>
<style>
  body {{ font-family: "Yu Gothic","Meiryo",sans-serif; background:#f4f5f7; color:#222; margin:0; padding:24px; }}
  .container {{ max-width: 980px; margin: 0 auto; }}
  .card {{ background:#fff; border-radius:10px; padding:24px 28px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,0.08); }}
  h1 {{ font-size: 1.5em; margin:0 0 4px; }}
  .sub {{ color:#666; font-size:0.9em; }}
  .price {{ font-size: 2.2em; font-weight:bold; margin: 8px 0; }}
  .change {{ font-size:1.1em; font-weight:bold; }}
  .signal-badge {{ display:inline-block; padding:6px 18px; border-radius:20px; font-weight:bold; font-size:1.3em; color:#fff; }}
  .grid2 {{ display:grid; grid-template-columns: 1fr 1fr; gap:20px; }}
  h2 {{ font-size:1.1em; border-left:4px solid #34495e; padding-left:10px; margin-top:0; }}
  ul {{ margin:6px 0; padding-left:20px; line-height:1.7; }}
  .score-track {{ position:relative; height:10px; background:linear-gradient(to right,#c0392b,#eee 50%,#1e8449); border-radius:5px; margin:10px 0 4px; }}
  .score-marker {{ position:absolute; top:-4px; width:4px; height:18px; border-radius:2px; }}
  .score-labels {{ display:flex; justify-content:space-between; font-size:0.75em; color:#888; }}
  table {{ width:100%; border-collapse: collapse; font-size:0.9em; }}
  td, th {{ padding:6px 8px; border-bottom:1px solid #eee; text-align:left; }}
  img {{ max-width:100%; border-radius:6px; }}
  .disclaimer {{ font-size:0.8em; color:#888; line-height:1.6; }}
  .footer {{ text-align:center; color:#999; font-size:0.8em; margin-top:10px; }}
</style>
<div class="container">

  <div class="card">
    <h1>{name}（{ticker_symbol}）</h1>
    <div class="sub">分析日時: {generated_at}</div>
    <div class="price">{sym}{last_close:,.0f}
      <span class="change" style="color:{change_color};">{'+' if change>=0 else ''}{change:,.0f}（{'+' if change_pct>=0 else ''}{change_pct:.2f}%）</span>
    </div>
    <div class="signal-badge" style="background:{'#1e8449' if combined['score']>=20 else ('#c0392b' if combined['score']<=-20 else '#7f8c8d')};">
      総合判定：{combined['label']}（スコア {combined['score']:+d}）
    </div>
    <div style="margin-top:16px;">{score_bar_html(combined['score'])}</div>
  </div>

  <div class="card grid2">
    <div>
      <h2>テクニカル分析（重み {combined['tech_weight']*100:.0f}%）　スコア: {tech['score']:+d}</h2>
      <ul>{tech_reasons}</ul>
    </div>
    <div>
      <h2>ファンダメンタルズ分析（重み {combined['fund_weight']*100:.0f}%）　スコア: {fund['score']:+d}</h2>
      <ul>{fund_reasons}</ul>
    </div>
  </div>

  <div class="card">
    <h2>価格チャート・出来高・RSI・MACD</h2>
    <img src="data:image/png;base64,{candle_img}" alt="candle chart">
  </div>

  <div class="card">
    <h2>簡易トレンド予測（{forecast['change_pct']:+.1f}% / 今後の傾向: {forecast['trend']}）</h2>
    <img src="data:image/png;base64,{forecast_img}" alt="forecast chart">
    <p class="disclaimer">
      ※このトレンド予測は過去{forecast['lookback_days']}営業日の株価推移を単純な線形回帰で機械的に延長したものです。
      決算発表・ニュース・市場全体の動向などは一切考慮していません。将来の株価を保証するものではなく、
      あくまで参考情報としてご利用ください。投資判断は自己責任で行ってください。
    </p>
  </div>

  <div class="card">
    <h2>主要指標</h2>
    <table>
      <tr><th>PER</th><td>{_fmt(info.get('trailingPE'), '倍')}</td>
          <th>PBR</th><td>{_fmt(info.get('priceToBook'), '倍')}</td></tr>
      <tr><th>配当利回り</th><td>{_fmt_optional_pct(get_dividend_yield_pct(info))}</td>
          <th>ROE</th><td>{_fmt_optional_pct(get_roe_pct(info))}</td></tr>
      <tr><th>時価総額</th><td>{_fmt_marketcap(info.get('marketCap'), info)}</td>
          <th>52週高値/安値</th><td>{_fmt(info.get('fiftyTwoWeekHigh'))} / {_fmt(info.get('fiftyTwoWeekLow'))}</td></tr>
      <tr><th>RSI(14)</th><td>{hist['RSI14'].iloc[-1]:.1f}</td>
          <th>出来高</th><td>{last['Volume']:,.0f}</td></tr>
    </table>
  </div>

  <div class="footer">
    本レポートはAIによる機械的な分析であり、投資助言ではありません。投資は自己判断・自己責任で行ってください。
  </div>
</div>
"""
    return html


def _fmt(v, unit=""):
    if v is None:
        return "N/A"
    try:
        return f"{v:,.2f}{unit}"
    except Exception:
        return str(v)


def _fmt_optional_pct(pct):
    if pct is None:
        return "N/A"
    return f"{pct:.2f}%"


_CURRENCY_SYMBOLS = {"JPY": "¥", "USD": "$", "EUR": "€", "GBP": "£"}


def currency_symbol(info: dict) -> str:
    code = (info or {}).get("currency") or "JPY"
    return _CURRENCY_SYMBOLS.get(code, code + " ")


def _fmt_marketcap(v, info=None):
    if v is None:
        return "N/A"
    currency = (info or {}).get("currency") or "JPY"
    if currency == "JPY":
        if v >= 1e12:
            return f"{v/1e12:.2f}兆円"
        if v >= 1e8:
            return f"{v/1e8:.1f}億円"
        return f"{v:,.0f}円"
    sym = currency_symbol(info)
    if v >= 1e12:
        return f"{sym}{v/1e12:.2f}T"
    if v >= 1e9:
        return f"{sym}{v/1e9:.2f}B"
    if v >= 1e6:
        return f"{sym}{v/1e6:.1f}M"
    return f"{sym}{v:,.0f}"


# ---------------------------------------------------------------------------
# コンソール出力
# ---------------------------------------------------------------------------

def print_console_report(ticker_symbol, name, hist, info, tech, fund, combined, forecast):
    last_close = hist["Close"].iloc[-1]
    sym = currency_symbol(info)
    print("=" * 60)
    print(f" {name}（{ticker_symbol}）  現在値: {sym}{last_close:,.0f}")
    print("=" * 60)
    print(f" 総合判定: {combined['label']}  (スコア {combined['score']:+d} / -100〜+100)")
    print(f"   - テクニカルスコア: {tech['score']:+d}")
    for r in tech["reasons"]:
        print(f"      ・{r}")
    print(f"   - ファンダメンタルズスコア: {fund['score']:+d}")
    for r in fund["reasons"]:
        print(f"      ・{r}")
    print(f" 簡易トレンド予測: 今後{forecast['change_pct']:+.1f}%（{forecast['trend']}）※参考値")
    print("-" * 60)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def analyze_one(code: str, forecast_days: int, tech_weight: float, output_dir: Path):
    ticker_symbol, hist, info = fetch_data(code)
    hist = compute_technical_indicators(hist)
    name = info.get("longName") or info.get("shortName") or ticker_symbol

    tech = technical_score(hist)
    fund = fundamental_score(info)
    combined = combined_signal(tech, fund, tech_weight)
    forecast = simple_forecast(hist, forecast_days=forecast_days)

    print_console_report(ticker_symbol, name, hist, info, tech, fund, combined, forecast)

    candle_img = make_candle_chart(hist, name)
    forecast_img = make_forecast_chart(hist, forecast, name)
    html = build_html_report(ticker_symbol, name, hist, info, tech, fund, combined, forecast, candle_img, forecast_img)

    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_code = ticker_symbol.replace(".", "_")
    out_path = output_dir / f"株価分析_{safe_code}_{date_str}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f" レポート出力: {out_path}")
    print("=" * 60)
    return out_path


def run_one_query(query: str, forecast_days: float, tech_weight: float, output_dir: Path, auto_open: bool):
    symbol = resolve_query(query)
    if not symbol:
        return
    try:
        out_path = analyze_one(symbol, forecast_days, tech_weight, output_dir)
        if auto_open and out_path is not None:
            try:
                os.startfile(out_path)
            except Exception:
                pass
    except Exception as e:
        print(f"[エラー] {query}: {e}", file=sys.stderr)


def interactive_loop(forecast_days: float, tech_weight: float, output_dir: Path):
    print("=" * 60)
    print(" 株予測ツール（対話モード）")
    print(" 証券コード（例: 7203）、ティッカー（例: AAPL）、")
    print(" または会社名（英語表記、例: Toyota）を入力してください。")
    print(" 複数銘柄はカンマ区切りで入力できます。")
    print(" 何も入力せず Enter を押すと終了します。")
    print("=" * 60)
    while True:
        raw = input("\n銘柄を入力 > ").strip()
        if not raw:
            print("終了します。")
            break
        for q in [q.strip() for q in raw.split(",") if q.strip()]:
            run_one_query(q, forecast_days, tech_weight, output_dir, auto_open=True)


def main():
    parser = argparse.ArgumentParser(description="ファンダメンタルズ×テクニカル分析による株予測ツール")
    parser.add_argument(
        "tickers", nargs="*",
        help="銘柄コード・ティッカー・会社名（例: 7203, 9984, AAPL, Toyota）。省略すると対話モードで入力できます。",
    )
    parser.add_argument("--forecast-days", type=int, default=10, help="トレンド予測日数（デフォルト10営業日）")
    parser.add_argument("--tech-weight", type=float, default=0.55, help="テクニカル分析の重み（0〜1、デフォルト0.55）")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR), help="HTML出力先ディレクトリ")
    parser.add_argument("--open", action="store_true", help="生成したHTMLレポートを既定のブラウザで自動的に開く")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if not args.tickers:
        interactive_loop(args.forecast_days, args.tech_weight, output_dir)
        return

    for query in args.tickers:
        run_one_query(query, args.forecast_days, args.tech_weight, output_dir, auto_open=args.open)


if __name__ == "__main__":
    main()
