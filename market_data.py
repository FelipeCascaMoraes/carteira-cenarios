import yfinance as yf
import requests
import numpy as np
import time
from datetime import datetime, timedelta
import streamlit as st  # adicione no topo

@st.cache_data(ttl=300, show_spinner=False)
def get_batch_prices(tickers):
    return {t: get_current_price(t) for t in tickers}

_cache: dict[str, tuple[float, float]] = {}
CACHE_TTL = 300

def _cache_get(ticker):
    if ticker in _cache:
        preco, ts = _cache[ticker]
        if time.time() - ts < CACHE_TTL:
            return preco
    return None

def _cache_set(ticker, preco):
    _cache[ticker] = (preco, time.time())

COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "ADA": "cardano", "XRP": "ripple",
    "DOGE": "dogecoin", "DOT": "polkadot", "MATIC": "matic-network", "AVAX": "avalanche-2",
}
CRYPTO_SYMBOLS = set(COINGECKO_IDS.keys())

TESOURO_TITULOS = {
    "SELIC2029":     "Tesouro Selic 2029",
    "SELIC2027":     "Tesouro Selic 2027",
    "IPCA2029":      "Tesouro IPCA+ 2029",
    "IPCA2035":      "Tesouro IPCA+ 2035",
    "IPCA2045":      "Tesouro IPCA+ 2045",
    "PREFIXADO2027": "Tesouro Prefixado 2027",
    "PREFIXADO2029": "Tesouro Prefixado 2029",
    "IPCARENDA2030": "Tesouro IPCA+ com Juros Semestrais 2030",
    "IPCARENDA2040": "Tesouro IPCA+ com Juros Semestrais 2040",
    "IPCARENDA2055": "Tesouro IPCA+ com Juros Semestrais 2055",
}
TESOURO_SYMBOLS = set(TESOURO_TITULOS.keys())

def is_crypto(ticker): return ticker.upper() in CRYPTO_SYMBOLS
def is_tesouro(ticker): return ticker.upper() in TESOURO_SYMBOLS

def _normalizar_ticker(ticker):
    t = ticker.upper().strip()
    if is_crypto(t) or is_tesouro(t): return t
    if "." in t: return t
    return t + ".SA"

def get_current_price(ticker):
    t = ticker.upper().strip()
    cached = _cache_get(t)
    if cached is not None: return cached
    if is_crypto(t): preco = _preco_cripto(t)
    elif is_tesouro(t): preco = _preco_tesouro(t)
    else: preco = _preco_acao(_normalizar_ticker(t))
    if preco is not None: _cache_set(t, preco)
    return preco

def _preco_acao(ticker_yf):
    try:
        hist = yf.Ticker(ticker_yf).history(period="2d")
        return float(hist["Close"].iloc[-1]) if not hist.empty else None
    except: return None

def _preco_cripto(ticker):
    coin_id = COINGECKO_IDS.get(ticker)
    if not coin_id: return None
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=brl"
        return float(requests.get(url, timeout=10).json()[coin_id]["brl"])
    except: return None

def _preco_tesouro(ticker):
    nome_titulo = TESOURO_TITULOS.get(ticker)
    if not nome_titulo: return None
    try:
        url = "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/Prices.json"
        titulos = requests.get(url, timeout=15).json()["response"]["TrsrBdTradgList"]
        for item in titulos:
            if nome_titulo.lower() in item["TrsrBd"]["nm"].lower():
                return float(item["TrsrBd"]["untrInvstmtVal"])
        return None
    except: return None

def get_historical_returns(ticker, days=252):
    t = ticker.upper().strip()
    if is_crypto(t): return _retornos_cripto(t, days)
    if is_tesouro(t): return None
    return _retornos_acao(_normalizar_ticker(t), days)

def _retornos_acao(ticker_yf, days):
    try:
        start = (datetime.today() - timedelta(days=days+30)).strftime("%Y-%m-%d")
        hist = yf.Ticker(ticker_yf).history(start=start)
        if len(hist) < 10: return None
        closes = hist["Close"].values
        return np.diff(closes) / closes[:-1]
    except: return None

def _retornos_cripto(ticker, days):
    coin_id = COINGECKO_IDS.get(ticker)
    if not coin_id: return None
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=brl&days={days+10}&interval=daily"
        prices = [p[1] for p in requests.get(url, timeout=15).json()["prices"]]
        if len(prices) < 10: return None
        arr = np.array(prices)
        return np.diff(arr) / arr[:-1]
    except: return None

def get_batch_prices(tickers):
    return {t: get_current_price(t) for t in tickers}