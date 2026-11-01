# -*- coding: utf-8 -*-
"""
株予測ツール共通ロジック
データ取得・テクニカル指標計算・スコアリング・簡易予測。
CLI版(stock_predictor.py)とWeb版(webapp/server.py)の両方から利用する。
"""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# データ取得・銘柄解決
# ---------------------------------------------------------------------------

def normalize_ticker(code: str) -> str:
    """4桁数字のみなら日本株として .T を付与する"""
    code = code.strip().upper()
    if code.isdigit() and "." not in code:
        return f"{code}.T"
    return code


# 主要な日本企業・米国企業の通称・和名エイリアス辞書。
# Yahoo Financeの検索API（yf.Search）は日本語の会社名（例:「トヨタ」）にはヒットしないため、
# よく検索されるであろう銘柄を補完する（追加のAPIキーや外部サービスは不要）。
_JP_COMPANY_ALIASES = [
    ("7203.T", "トヨタ自動車", ["トヨタ", "トヨタ自動車"]),
    ("7267.T", "本田技研工業（ホンダ）", ["ホンダ", "本田技研", "本田技研工業"]),
    ("7201.T", "日産自動車", ["日産", "日産自動車"]),
    ("7269.T", "スズキ", ["スズキ"]),
    ("7202.T", "いすゞ自動車", ["いすゞ", "いすゞ自動車"]),
    ("6758.T", "ソニーグループ", ["ソニー", "ソニーグループ"]),
    ("9984.T", "ソフトバンクグループ", ["ソフトバンクグループ", "ソフトバンクg"]),
    ("9434.T", "ソフトバンク", ["ソフトバンク"]),
    ("7974.T", "任天堂", ["任天堂"]),
    ("6861.T", "キーエンス", ["キーエンス"]),
    ("8306.T", "三菱UFJフィナンシャル・グループ", ["三菱ufj", "三菱ufj銀行", "mufg"]),
    ("8316.T", "三井住友フィナンシャルグループ", ["三井住友", "smbc", "三井住友銀行"]),
    ("8411.T", "みずほフィナンシャルグループ", ["みずほ", "みずほ銀行"]),
    ("4063.T", "信越化学工業", ["信越化学"]),
    ("6098.T", "リクルートホールディングス", ["リクルート"]),
    ("9432.T", "日本電信電話", ["ntt", "日本電信電話"]),
    ("9433.T", "KDDI", ["kddi", "ケーディーディーアイ"]),
    ("4502.T", "武田薬品工業", ["武田薬品", "武田"]),
    ("4519.T", "中外製薬", ["中外製薬"]),
    ("4568.T", "第一三共", ["第一三共"]),
    ("4523.T", "エーザイ", ["エーザイ"]),
    ("6501.T", "日立製作所", ["日立", "日立製作所"]),
    ("6502.T", "東芝", ["東芝"]),
    ("6503.T", "三菱電機", ["三菱電機"]),
    ("6752.T", "パナソニックホールディングス", ["パナソニック"]),
    ("6702.T", "富士通", ["富士通"]),
    ("6701.T", "日本電気", ["nec", "日本電気"]),
    ("8058.T", "三菱商事", ["三菱商事"]),
    ("8031.T", "三井物産", ["三井物産"]),
    ("8001.T", "伊藤忠商事", ["伊藤忠", "伊藤忠商事"]),
    ("8053.T", "住友商事", ["住友商事"]),
    ("2914.T", "日本たばこ産業", ["jt", "日本たばこ"]),
    ("9020.T", "東日本旅客鉄道", ["jr東日本"]),
    ("9021.T", "西日本旅客鉄道", ["jr西日本"]),
    ("9022.T", "東海旅客鉄道", ["jr東海"]),
    ("9101.T", "日本郵船", ["日本郵船"]),
    ("9104.T", "商船三井", ["商船三井"]),
    ("7011.T", "三菱重工業", ["三菱重工"]),
    ("7012.T", "川崎重工業", ["川崎重工"]),
    ("5401.T", "日本製鉄", ["日本製鉄"]),
    ("5108.T", "ブリヂストン", ["ブリヂストン"]),
    ("4901.T", "富士フイルムホールディングス", ["富士フイルム"]),
    ("4911.T", "資生堂", ["資生堂"]),
    ("2502.T", "アサヒグループホールディングス", ["アサヒ", "アサヒビール"]),
    ("2503.T", "キリンホールディングス", ["キリン", "キリンビール"]),
    ("3382.T", "セブン&アイ・ホールディングス", ["セブンイレブン", "セブンアンドアイ", "セブン&アイ"]),
    ("9983.T", "ファーストリテイリング", ["ユニクロ", "ファーストリテイリング"]),
    ("8267.T", "イオン", ["イオン"]),
    ("9843.T", "ニトリホールディングス", ["ニトリ"]),
    ("4755.T", "楽天グループ", ["楽天"]),
    ("4661.T", "オリエンタルランド", ["オリエンタルランド", "ディズニー"]),
    ("6178.T", "日本郵政", ["日本郵政"]),
    ("8750.T", "第一生命ホールディングス", ["第一生命"]),
    ("8766.T", "東京海上ホールディングス", ["東京海上"]),
    ("8801.T", "三井不動産", ["三井不動産"]),
    ("8802.T", "三菱地所", ["三菱地所"]),
    ("9201.T", "日本航空", ["jal", "日本航空"]),
    ("9202.T", "ANAホールディングス", ["ana", "全日空"]),
    ("6367.T", "ダイキン工業", ["ダイキン"]),
    ("6301.T", "コマツ", ["コマツ"]),
    ("6954.T", "ファナック", ["ファナック"]),
    ("6971.T", "京セラ", ["京セラ"]),
    ("6981.T", "村田製作所", ["村田製作所"]),
    ("6857.T", "アドバンテスト", ["アドバンテスト"]),
    ("8035.T", "東京エレクトロン", ["東京エレクトロン"]),
    ("AAPL", "アップル", ["アップル"]),
    ("GOOGL", "アルファベット（グーグル）", ["グーグル"]),
    ("AMZN", "アマゾン・ドット・コム", ["アマゾン"]),
    ("MSFT", "マイクロソフト", ["マイクロソフト"]),
    ("TSLA", "テスラ", ["テスラ"]),
    ("NVDA", "エヌビディア", ["エヌビディア"]),
    ("META", "メタ・プラットフォームズ", ["メタ", "フェイスブック"]),
    ("NFLX", "ネットフリックス", ["ネットフリックス"]),
]

_JP_ALIAS_INDEX = [
    (alias, symbol, name)
    for symbol, name, aliases in _JP_COMPANY_ALIASES
    for alias in aliases
]


def _search_jp_aliases(query: str, max_results: int):
    q = query.strip().lower()
    if not q:
        return []
    matches = []
    seen = set()
    for alias, symbol, name in _JP_ALIAS_INDEX:
        if symbol in seen:
            continue
        if q in alias or alias in q:
            seen.add(symbol)
            matches.append({
                "symbol": symbol,
                "shortname": name,
                "longname": name,
                "exchDisp": "Tokyo Stock Exchange" if symbol.endswith(".T") else "NASDAQ/NYSE",
                "quoteType": "EQUITY",
            })
        if len(matches) >= max_results:
            break
    return matches


def search_quotes(query: str, max_results: int = 8):
    """会社名などのあいまいな入力から候補一覧を取得する。
    日本語の通称・和名（例:「トヨタ」）はまずローカル辞書から補完し、
    そのうえでyfinanceのオンライン検索結果をマージする。"""
    jp_matches = _search_jp_aliases(query, max_results)
    try:
        online = yf.Search(query, max_results=max_results).quotes
        online = [r for r in online if r.get("symbol") and r.get("quoteType") == "EQUITY"]
    except Exception:
        online = []

    seen = {m["symbol"] for m in jp_matches}
    merged = jp_matches + [r for r in online if r.get("symbol") not in seen]
    return merged[:max_results]


def resolve_query_auto(query: str):
    """入力文字列から実際のティッカーシンボルを解決する（対話なし・自動で最有力候補を採用）。
    証券コード／ティッカーはそのまま、会社名は検索結果の1件目を採用する。"""
    query = query.strip().lstrip("﻿")
    if not query:
        return None, []
    compact = query.replace(".", "")
    if compact.isdigit():
        return normalize_ticker(query), []
    # 日本語などの非ASCII文字はティッカーになり得ないため、必ず候補検索に回す
    # （Pythonのstr.isalpha()はカタカナ・漢字もTrueを返すため、isascii()判定が必須）。
    if query.isascii() and query.replace(".", "").isalpha() and len(query) <= 6 and " " not in query:
        return query.upper(), []

    candidates = search_quotes(query)
    if not candidates:
        return None, []
    return candidates[0].get("symbol"), candidates


def fetch_data(code: str, period: str = "1y"):
    """常にyfinanceへ問い合わせて最新の株価履歴・企業情報を取得する"""
    ticker_symbol = normalize_ticker(code)
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period=period, auto_adjust=False)
    if hist.empty:
        raise ValueError(f"銘柄コード '{code}' のデータが取得できませんでした。コードを確認してください。")
    # 取引時間中は当日分の足が未確定（Close等がNaN）のことがあるため、
    # 指標計算にはそれを除いた確定済みの足のみを使用する
    complete_mask = hist[["Open", "High", "Low", "Close"]].notna().all(axis=1)
    hist = hist[complete_mask]
    if hist.empty:
        raise ValueError(f"銘柄コード '{code}' の確定済みデータが取得できませんでした。")
    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}
    return ticker_symbol, hist, info


def get_live_price(info: dict, hist: pd.DataFrame):
    """取引時間中も追従するライブ価格（当日の未確定値を含む）を取得する。
    取得できない場合は確定済みの最終終値にフォールバックする。"""
    for key in ("currentPrice", "regularMarketPrice"):
        v = info.get(key)
        if v is not None:
            return v
    return hist["Close"].iloc[-1]


def get_prev_close(info: dict, hist: pd.DataFrame):
    """前日終値。ライブ価格との差分（前日比）の基準に使う。"""
    v = info.get("previousClose")
    if v is not None:
        return v
    return hist["Close"].iloc[-2] if len(hist) > 1 else hist["Close"].iloc[-1]


def fetch_news(ticker_symbol: str, max_items: int = 10):
    """Yahoo Financeの関連ニュース見出しを取得する（無料・追加API不要）。
    yfinanceのバージョンによりレスポンス形式が異なるため両対応する。"""
    try:
        raw = yf.Ticker(ticker_symbol).news or []
    except Exception:
        return []

    items = []
    for n in raw[:max_items]:
        content = n.get("content") if isinstance(n.get("content"), dict) else None
        if content:
            title = content.get("title")
            publisher = (content.get("provider") or {}).get("displayName", "")
            pub_date = content.get("pubDate")
            link = (
                (content.get("canonicalUrl") or {}).get("url")
                or (content.get("clickThroughUrl") or {}).get("url")
            )
        else:
            title = n.get("title")
            publisher = n.get("publisher", "")
            ts = n.get("providerPublishTime")
            pub_date = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None
            link = n.get("link")
        if not title:
            continue
        items.append({"title": title, "publisher": publisher, "pub_date": pub_date, "link": link})
    return items


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
            reasons.append("PERがマイナス（赤字）で割高感（-20）")
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


_NEWS_POSITIVE_KEYWORDS = [
    "surge", "soar", "rally", "record high", "all-time high", "beats estimates",
    "beat expectations", "upgrade", "outperform", "raises guidance", "raises forecast",
    "strong demand", "expands", "breakthrough", "deal", "agreement", "stimulus",
    "rate cut", "tariff cut", "ceasefire", "recovery", "buyback", "profit jump",
]
_NEWS_NEGATIVE_KEYWORDS = [
    "plunge", "slump", "tumble", "sink", "downgrade", "underperform", "cuts guidance",
    "cuts forecast", "recall", "lawsuit", "investigation", "sanction", "tariff",
    "war", "conflict", "recession", "inflation surge", "rate hike", "layoff",
    "bankruptcy", "crash", "warns", "shortage", "strike", "probe", "fraud",
]


def world_affairs_score(news_items: list) -> dict:
    """関連ニュース見出しのキーワードから世界情勢・市場センチメントを簡易評価する
    （生成AIは使わず、キーワードマッチのルールベース判定）。"""
    if not news_items:
        return {
            "score": 0,
            "reasons": ["関連ニュースが取得できなかったため中立としました（±0）"],
            "news": [],
        }

    reasons = []
    score = 0
    hits = 0
    for item in news_items:
        title = item["title"]
        lower = title.lower()
        pos_hit = next((kw for kw in _NEWS_POSITIVE_KEYWORDS if kw in lower), None)
        neg_hit = next((kw for kw in _NEWS_NEGATIVE_KEYWORDS if kw in lower), None)
        if pos_hit and not neg_hit:
            score += 8
            reasons.append(f"好材料ニュース「{title}」（+8）")
            hits += 1
        elif neg_hit and not pos_hit:
            score -= 8
            reasons.append(f"悪材料ニュース「{title}」（-8）")
            hits += 1

    if hits == 0:
        reasons.append(f"直近{len(news_items)}件のニュース見出しに明確な好悪材料は見つかりませんでした（±0）")

    score = max(-100, min(100, score))
    return {"score": score, "reasons": reasons, "news": news_items}


_DEFAULT_TECH_WEIGHT = 0.45
_DEFAULT_FUND_WEIGHT = 0.35
_DEFAULT_WORLD_WEIGHT = 0.20


def combined_signal(tech: dict, fund: dict, world: dict, tech_weight: float = _DEFAULT_TECH_WEIGHT) -> dict:
    """テクニカル・ファンダメンタルズ・世界情勢の3専門エージェントによる加重平均チーム評価。
    tech_weightのみ指定された場合、残りはファンダメンタルズ:世界情勢＝35:20の既定比率で配分する。"""
    remaining = 1 - tech_weight
    fund_ratio = _DEFAULT_FUND_WEIGHT / (_DEFAULT_FUND_WEIGHT + _DEFAULT_WORLD_WEIGHT)
    fund_weight = remaining * fund_ratio
    world_weight = remaining * (1 - fund_ratio)

    total = tech["score"] * tech_weight + fund["score"] * fund_weight + world["score"] * world_weight
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

    return {
        "score": total,
        "label": label,
        "tech_weight": tech_weight,
        "fund_weight": fund_weight,
        "world_weight": world_weight,
    }


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
# 表示用フォーマット
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOLS = {"JPY": "¥", "USD": "$", "EUR": "€", "GBP": "£"}


def currency_symbol(info: dict) -> str:
    code = (info or {}).get("currency") or "JPY"
    return _CURRENCY_SYMBOLS.get(code, code + " ")


def format_marketcap(v, info=None):
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


def analyze(code: str, forecast_days: int = 10, tech_weight: float = _DEFAULT_TECH_WEIGHT):
    """1銘柄分のフル分析結果を辞書で返す共通エントリポイント。
    テクニカル・ファンダメンタルズ・世界情勢（ニュース見出し）の3専門エージェントで
    それぞれスコアリングし、加重平均でチーム評価（総合判定）を算出する。"""
    ticker_symbol, hist, info = fetch_data(code)
    hist = compute_technical_indicators(hist)
    name = info.get("longName") or info.get("shortName") or ticker_symbol

    tech = technical_score(hist)
    fund = fundamental_score(info)
    news_items = fetch_news(ticker_symbol)
    world = world_affairs_score(news_items)
    combined = combined_signal(tech, fund, world, tech_weight)
    forecast = simple_forecast(hist, forecast_days=forecast_days)
    live_price = get_live_price(info, hist)
    prev_close = get_prev_close(info, hist)

    return {
        "ticker_symbol": ticker_symbol,
        "name": name,
        "hist": hist,
        "info": info,
        "tech": tech,
        "fund": fund,
        "world": world,
        "combined": combined,
        "forecast": forecast,
        "live_price": live_price,
        "prev_close": prev_close,
    }
