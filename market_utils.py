import yfinance as yf

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
            
            # Try to get short name, fallback to symbol
            name = symbol
            try:
                # Some versions of yfinance put metadata in .info dict which triggers a separate request
                # We'll try to keep it fast, but if we need name, we might need .info
                # maximizing speed: use symbol as name if fetching full info is too slow/rate-limited
                # let's try getting name from ticker.info only if needed, or just use symbol
                name = ticker.info.get('shortName', symbol) 
            except:
                pass

            return {
                'symbol': symbol.upper(),
                'name': name,
                'price': round(price, 2),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'color': 'green' if change >= 0 else 'red'
            }
        else:
             return {'error': 'Data not found for symbol'}

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {'error': str(e)}
