import yfinance as yf
import time
import threading

# Thread-safe Cache
_market_cache = {}
_cache_lock = threading.Lock()

def get_cached_data(key, expiry_seconds):
    with _cache_lock:
        if key in _market_cache:
            data, timestamp = _market_cache[key]
            if time.time() - timestamp < expiry_seconds:
                return data
        return None

def set_cached_data(key, data):
    with _cache_lock:
        _market_cache[key] = (data, time.time())

def get_market_summary():
    """
    Fetches real-time data for major global indices.
    """
    # Symbol mapping for major indices
    # ^GSPC: S&P 500 (US)
    # ^IXIC: Nasdaq (US)
    # ^DJI: Dow Jones (US)
    # ^FTSE: FTSE 100 (UK)
    # ^NSEI: Nifty 50 (India)
    # ^N225: Nikkei 225 (Japan)
    # ^GDAXI: DAX (Germany)
    # BTC-USD: Bitcoin (Crypto)
    
    cache_key = 'market_summary'
    cached = get_cached_data(cache_key, 300) # 5 min expiry
    if cached:
        return cached

    symbols = ['^GSPC', '^IXIC', '^DJI', '^FTSE', '^NSEI', '^N225', '^GDAXI', 'BTC-USD']
    
    market_data = []
    
    try:
        # Fetch data in bulk for efficiency
        tickers = yf.Tickers(' '.join(symbols))
        
        for symbol in symbols:
            try:
                ticker = tickers.tickers[symbol]
                info = ticker.fast_info
                
                # Some indices might not have fast_info populated correctly depending on yfinance version/API state
                # We try fast_info first (real-time-ish), fall back to history if needed
                
                price = info.last_price
                prev_close = info.previous_close
                
                if price and prev_close:
                    change = price - prev_close
                    change_percent = (change / prev_close) * 100
                    
                    name = get_symbol_name(symbol)
                    
                    market_data.append({
                        'symbol': symbol,
                        'name': name,
                        'price': round(price, 2),
                        'change': round(change, 2),
                        'change_percent': round(change_percent, 2),
                        'color': 'green' if change >= 0 else 'red'
                    })
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                
    except Exception as e:
        print(f"Global error fetching market data: {e}")
        
        
    if market_data:
        set_cached_data(cache_key, market_data)

    return market_data

def get_symbol_name(symbol):
    names = {
        '^GSPC': 'S&P 500',
        '^IXIC': 'Nasdaq',
        '^DJI': 'Dow Jones',
        '^FTSE': 'FTSE 100',
        '^NSEI': 'Nifty 50',
        '^N225': 'Nikkei 225',
        '^GDAXI': 'DAX',
        'BTC-USD': 'Bitcoin'
    }
    return names.get(symbol, symbol)

def get_stock_data(symbol):
    """
    Fetches real-time data for a specific stock symbol.
    """
    cache_key = f"stock_{symbol.upper()}"
    cached = get_cached_data(cache_key, 120) # 2 min expiry for stocks
    if cached:
        return cached

    try:
        # Validate symbol (basic alphanumeric check)
        if not symbol.replace('.','').replace('-','').isalnum():
            return {'error': 'Invalid symbol format'}
            
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        
        price = info.last_price
        prev_close = info.previous_close
        
        if price is None:
             # Fallback to history for some tickers if fast_info fails
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                prev_close = hist['Open'].iloc[-1] # Approximation for intraday change if prev_close missing
        
        if price:
            change = 0
            change_percent = 0
            if prev_close:
                change = price - prev_close
                change_percent = (change / prev_close) * 100
            
            # Additional advanced metadata
            day_high = info.get('dayHigh')
            day_low = info.get('dayLow')
            volume = info.get('lastVolume')
            currency = info.get('currency', 'USD')

            # Try to get short name, fallback to symbol
            name = symbol
            try:
                # Optimized name fetching
                name = ticker.info.get('shortName', symbol) 
            except:
                pass

            return {
                'symbol': symbol.upper(),
                'name': name,
                'price': round(price, 2),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'high': round(day_high, 2) if day_high else None,
                'low': round(day_low, 2) if day_low else None,
                'volume': volume,
                'currency': currency,
                'color': 'green' if change >= 0 else 'red'
            }
        else:
             return {'error': 'Data not found for symbol'}

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {'error': str(e)}
    
    if 'error' not in data:
        set_cached_data(cache_key, data)
    
    return data

def get_technical_indicators(symbol):
    """
    Calculates basic technical indicators (SMA20, RSI).
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")
        if hist.empty or len(hist) < 15:
            return None
        
        # RSI Calculation
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # SMA 20 (or max available)
        sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        if not sma_20:
             sma_20 = hist['Close'].mean()

        return {
            'sma_20': round(sma_20, 2),
            'rsi': round(current_rsi, 2),
            'signal': 'OVERBOUGHT' if current_rsi > 70 else ('OVERSOLD' if current_rsi < 30 else 'NEUTRAL')
        }
    except Exception as e:
        print(f"Indicator error for {symbol}: {e}")
        return None
