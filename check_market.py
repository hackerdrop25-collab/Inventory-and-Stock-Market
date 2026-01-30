from market_utils import get_market_summary
import time

def print_market_data():
    print("\n" + "="*50)
    print(f" GLOBAL MARKET SUMMARY - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    print(f"{'INDEX':<15} {'PRICE':<12} {'CHANGE':<10} {'% CHANGE':<10}")
    print("-" * 50)
    
    data = get_market_summary()
    
    if not data:
        print("No data received. Check internet connection or API status.")
        return

    for item in data:
        symbol_name = item['name']
        price = f"{item['price']:.2f}"
        change = f"{item['change']:.2f}"
        pct = f"{item['change_percent']:.2f}%"
        
        # Add basic implementation of colors for terminal if possible, otherwise plain text
        # Using ANSI escape codes for basic colors
        GREEN = '\033[92m'
        RED = '\033[91m'
        RESET = '\033[0m'
        
        color_code = GREEN if item['change'] >= 0 else RED
        
        print(f"{symbol_name:<15} {price:<12} {color_code}{change:<10} {pct:<10}{RESET}")
        
    print("="*50 + "\n")

if __name__ == "__main__":
    print("Fetching real-time data from Yahoo Finance...")
    print_market_data()
