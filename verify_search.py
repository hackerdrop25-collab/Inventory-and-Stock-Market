from market_utils import get_stock_data
import sys

def test_search(symbol):
    print(f"Searching for {symbol}...")
    data = get_stock_data(symbol)
    if 'error' in data:
        print(f"Error: {data['error']}")
    else:
        print(f"Found: {data['name']} ({data['symbol']})")
        print(f"Price: {data['price']}")
        print(f"Change: {data['change']} ({data['change_percent']}%)")
    print("-" * 30)

if __name__ == "__main__":
    test_search("AAPL")
    test_search("TSLA")
    test_search("MSFT")
    # Test an invalid one
    test_search("INVALID123")
