import yfinance as yf
from datetime import datetime
import json

class NewsService:
    def get_symbol_news(self, symbol):
        """
        Fetches recent news for a given stock symbol using yfinance.
        """
        try:
            ticker = yf.Ticker(symbol)
            # yfinance returns a list of news dictionaries
            news = ticker.news
            
            formatted_news = []
            if news:
                for item in news[:10]: # Get top 10
                    formatted_news.append({
                        'title': item.get('title'),
                        'publisher': item.get('publisher'),
                        'link': item.get('link'),
                        'time': datetime.fromtimestamp(item.get('providerPublishTime')).strftime('%Y-%m-%d %H:%M') if item.get('providerPublishTime') else 'Recently',
                        'thumbnail': item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url') if item.get('thumbnail') else None
                    })
            return formatted_news
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []

    def get_market_news(self):
        """
        Fetches general market news using major indices.
        """
        return self.get_symbol_news('^GSPC')

# Global Instance
news_service = NewsService()
