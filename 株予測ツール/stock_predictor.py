# -*- coding: utf-8 -*-
"""
株予測ツール（CLI版）
ファンダメンタルズ分析とテクニカル分析を組み合わせ、売買シグナルと
簡易的な株価トレンド予測を行い、自己完結型のHTMLレポートを出力する。

使い方:
    py stock_predictor.py                    # 対話モード（銘柄コード・会社名を入力して分析）
    py stock_predictor.py 7203
    py stock_predictor.py 7203 9984 6758 --forecast-days 15
    py stock_predictor.py 7203 --tech-weight 0.7
    py stock_predictor.py "Toyota"            # 会社名（英語表記）でも検索可能

常にオンラインでyfinanceから最新データを取得する。
ブラウザでリアルタイムに使いたい場合は webapp/ のWeb版を利用のこと。

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

from analysis_core import (
    analyze,
    currency_symbol,
    format_marketcap,
    get_dividend_yield_pct,
    get_roe_pct,
    resolve_query_auto,
)

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
# 銘柄解決（対話的な候補選択つき）
# ---------------------------------------------------------------------------

def resolve_query_interactive(query: str):
    """CLI向け：会社名検索で複数候補があれば対話的に選択させる"""
    symbol, candidates = resolve_query_auto(query)
    if symbol and len(candidates) <= 1:
        return symbol

    if not candidates:
        # resolve_query_autoが証券コード/ティッカーとして即決した場合
        if symbol:
            return symbol
        print(
            f"'{query}' に一致する銘柄が見つかりませんでした。"
            " 会社名は英語表記（例: Toyota, SoftBank）か、証券コード（例: 7203）でお試しください。"
        )
        return None

    print(f"\n'{query}' の検索結果:")
    for i, r in enumerate(candidates, 1):
        display_name = r.get("shortname") or r.get("longname") or ""
        print(f"  {i}. {r.get('symbol'):<10} {display_name}  ({r.get('exchDisp', '')})")
    sel = input("番号を選択してください（Enterで1番目）: ").strip()
    if not sel:
        chosen = candidates[0]
    else:
        try:
            chosen = candidates[int(sel) - 1]
        except (ValueError, IndexError):
            print("無効な選択のため1番目を使用します。")
            chosen = candidates[0]

    chosen_symbol = chosen.get("symbol")
    display_name = chosen.get("shortname") or chosen.get("longname") or chosen_symbol
    print(f"→ {chosen_symbol}（{display_name}）を使用します。")
    return chosen_symbol


# ---------------------------------------------------------------------------
# チャート生成（base64埋め込み用）
# ---------------------------------------------------------------------------

def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def make_candle_chart(df, name: str) -> str:
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


def make_forecast_chart(df, forecast: dict, name: str) -> str:
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


def build_html_report(ticker_symbol, name, hist, info, live_price, prev_close, tech, fund, combined, forecast, candle_img, forecast_img) -> str:
    last = hist.iloc[-1]
    change = live_price - prev_close
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
    <div class="price">{sym}{live_price:,.0f}
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
      <tr><th>時価総額</th><td>{format_marketcap(info.get('marketCap'), info)}</td>
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


# ---------------------------------------------------------------------------
# コンソール出力
# ---------------------------------------------------------------------------

def print_console_report(ticker_symbol, name, live_price, info, tech, fund, combined, forecast):
    sym = currency_symbol(info)
    print("=" * 60)
    print(f" {name}（{ticker_symbol}）  現在値: {sym}{live_price:,.0f}")
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
    result = analyze(code, forecast_days=forecast_days, tech_weight=tech_weight)
    ticker_symbol = result["ticker_symbol"]
    name = result["name"]
    hist = result["hist"]
    info = result["info"]
    tech = result["tech"]
    fund = result["fund"]
    combined = result["combined"]
    forecast = result["forecast"]
    live_price = result["live_price"]
    prev_close = result["prev_close"]

    print_console_report(ticker_symbol, name, live_price, info, tech, fund, combined, forecast)

    candle_img = make_candle_chart(hist, name)
    forecast_img = make_forecast_chart(hist, forecast, name)
    html = build_html_report(
        ticker_symbol, name, hist, info, live_price, prev_close,
        tech, fund, combined, forecast, candle_img, forecast_img,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    safe_code = ticker_symbol.replace(".", "_")
    out_path = output_dir / f"株価分析_{safe_code}_{date_str}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f" レポート出力: {out_path}")
    print("=" * 60)
    return out_path


def run_one_query(query: str, forecast_days: float, tech_weight: float, output_dir: Path, auto_open: bool):
    symbol = resolve_query_interactive(query)
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
