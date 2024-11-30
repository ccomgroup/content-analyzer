import json
import hashlib
import os

class CacheManager:
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, url):
        return hashlib.md5(url.encode()).hexdigest()
    
    def get_cached_result(self, url):
        cache_key = self.get_cache_key(url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def save_to_cache(self, url, result):
        cache_key = self.get_cache_key(url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        with open(cache_file, 'w') as f:
            json.dump(result, f) 