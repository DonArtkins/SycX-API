from functools import wraps
from flask import request, current_app
import time
from collections import defaultdict
import threading

class RateLimiter:
    def __init__(self):
        self.request_counts = defaultdict(list)
        self.lock = threading.Lock()

    def is_rate_limited(self, ip):
        with self.lock:
            now = time.time()
            window = current_app.config['RATE_LIMIT_PERIOD'].total_seconds()
            
            # Clean old requests
            self.request_counts[ip] = [
                req_time for req_time in self.request_counts[ip]
                if now - req_time < window
            ]
            
            # Check rate limit
            if len(self.request_counts[ip]) >= current_app.config['RATE_LIMIT']:
                return True
                
            self.request_counts[ip].append(now)
            return False

rate_limiter = RateLimiter()

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        
        if rate_limiter.is_rate_limited(ip):
            return {
                'error': 'Rate limit exceeded',
                'retry_after': current_app.config['RATE_LIMIT_PERIOD'].total_seconds()
            }, 429
            
        return f(*args, **kwargs)
    return decorated_function
