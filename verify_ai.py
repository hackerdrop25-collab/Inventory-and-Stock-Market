from gemini_ai import ai_assistant
from market_utils import get_market_summary
import json

def verify_ai():
    print("Verifying Gemini AI Assistant...")
    
    # 1. Test Market Insights
    print("\n[1/2] Testing Market Insights...")
    market_data = get_market_summary()
    if market_data:
        insights = ai_assistant.get_market_insights(market_data)
        print(f"Result: {insights}")
    else:
        print("Skipping market insights (no data).")
        
    # 2. Test Inventory Advice
    print("\n[2/2] Testing Inventory Advice...")
    low_stock = [{'name': 'Test Item', 'quantity': 2}]
    top_sales = [{'name': 'Best Seller', 'revenue': 1000}]
    advice = ai_assistant.get_inventory_advice(low_stock, top_sales)
    print(f"Result: {advice}")
    
    print("\nVerification Complete!")

if __name__ == "__main__":
    verify_ai()
