import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

class GeminiAI:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            print("WARNING: GEMINI_API_KEY not found. AI features will be in mock mode.")

    def get_market_insights(self, market_data):
        """
        Analyzes market data and returns a professional insight summary.
        """
        if not self.model:
            return "AI Oracle: Connect your Gemini API key to receive real-time market sentiment analysis and trading signals."

        prompt = f"""
        Act as a professional financial analyst. Analyze the following market indices and provide a concise (2-3 sentence) summary of the global market sentiment. 
        Identify if it's a 'Bullish', 'Bearish', or 'Neutral' day and give one key reason why.
        
        Data: {json.dumps(market_data)}
        
        Format: "Market Sentiment: [Sentiment]. [Insight]"
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"AI Error: Unable to fetch insights. ({str(e)})"

    def get_inventory_advice(self, low_stock_items, top_sales_items):
        """
        Provides advice on inventory management based on stock levels and recent performance.
        """
        if not self.model:
            return "AI Suggestion: Restock items that are below 5 units to ensure business continuity."

        prompt = f"""
        Act as an inventory optimization expert. Based on the following stock data, provide 3 actionable bullet points for the manager.
        - Low Stock Items (needs attention): {json.dumps(low_stock_items)}
        - Top Performing Items (trending): {json.dumps(top_sales_items)}
        
        Keep it professional and concise.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"AI Error: Unable to generate advice. ({str(e)})"

# Global Instance
ai_assistant = GeminiAI()
