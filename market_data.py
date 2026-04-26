import yfinance as yf
import requests
import numpy as np
import time
from datetime import datetime, timedelta

_cache: dict[str, tuple[float, float]] = {}  # ticker → (preço, timestamp)
CACHE_TTL = 300  # 5 minutos


def _cache_get(ticker: str) -> float | None:
    if ticker in _cache:
        preco, ts = _cache[ticker]
        if time.time() - ts < CACHE_TTL:
            return preco
    return None


def _cache_set(ticker: str, preco: float):
    _cache[ticker] = (preco, time.time())

COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "AVAX": "avalanche-2",
}

CRYPTO_SYMBOLS = set(COINGECKO_IDS.keys())

def is_crypto(ticker: str) -> bool:
    return ticker.upper() in CRYPTO_SYMBOLS

def _normalizar_ticker(ticker: str) -> str:
    """Adiciona .SA se for ação BR (sem ponto, sem cripto)."""
    t = ticker.upper().strip()
    if is_crypto(t):
        return t
    if "." in t:
        return t
    return t + ".SA"

def get_current_price(ticker: str) -> float | None:
    t = ticker.upper().strip()
    if is_crypto(t):
        return _preco_cripto(t)
    return _preco_acao(_normalizar_ticker(t))


def _preco_acao(ticker_yf: str) -> float | None:
    try:
        hist = yf.Ticker(ticker_yf).history(period="2d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def _preco_cripto(ticker: str) -> float | None:
    coin_id = COINGECKO_IDS.get(ticker)
    if not coin_id:
        return None
    try:
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={coin_id}&vs_currencies=brl"
        )
        data = requests.get(url, timeout=10).json()
        return float(data[coin_id]["brl"])
    except Exception:
        return None


def get_historical_returns(ticker: str, days: int = 252) -> np.ndarray | None:
    """Retorna array de retornos diários. Usado para calcular volatilidade."""
    t = ticker.upper().strip()
    if is_crypto(t):
        return _retornos_cripto(t, days)
    return _retornos_acao(_normalizar_ticker(t), days)


def _retornos_acao(ticker_yf: str, days: int) -> np.ndarray | None:
    try:
        start = (datetime.today() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
        hist = yf.Ticker(ticker_yf).history(start=start)
        if len(hist) < 10:
            return None
        closes = hist["Close"].values
        return np.diff(closes) / closes[:-1]
    except Exception:
        return None


def _retornos_cripto(ticker: str, days: int) -> np.ndarray | None:
    coin_id = COINGECKO_IDS.get(ticker)
    if not coin_id:
        return None
    try:
        url = (
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            f"?vs_currency=brl&days={days + 10}&interval=daily"
        )
        prices = [p[1] for p in requests.get(url, timeout=15).json()["prices"]]
        if len(prices) < 10:
            return None
        arr = np.array(prices)
        return np.diff(arr) / arr[:-1]
    except Exception:
        return None


def get_batch_prices(tickers: list[str]) -> dict[str, float | None]:
    return {t: get_current_price(t) for t in tickers}