from market_utils import get_market_summary
import time

def test_cache():
    print("Testing cache performance...")
    
    # First call (should be slow, fetching from network)
    start_time = time.time()
    get_market_summary()
    first_duration = time.time() - start_time
    print(f"First call took: {first_duration:.4f} seconds")
    
    # Second call (should be fast, from cache)
    start_time = time.time()
    get_market_summary()
    second_duration = time.time() - start_time
    print(f"Second call took: {second_duration:.4f} seconds")
    
    if second_duration < first_duration / 2:
        print("SUCCESS: Cache is working effectively!")
    else:
        print("WARNING: Cache speedup might be less than expected (or first call was also fast).")

if __name__ == "__main__":
    test_cache()
