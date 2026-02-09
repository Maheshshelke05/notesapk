from geopy.distance import geodesic
from datetime import datetime, timedelta
from typing import Tuple
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        
        if len(self.requests[key]) >= max_requests:
            return False
        
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter()

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers"""
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

def is_within_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> bool:
    """Check if two locations are within specified radius"""
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    return distance <= radius_km

def reset_daily_counter_if_needed(user, field_name: str, reset_date_field: str):
    """Reset daily counter if date has changed"""
    now = datetime.utcnow()
    reset_date = getattr(user, reset_date_field)
    
    if reset_date.date() < now.date():
        setattr(user, field_name, 0)
        setattr(user, reset_date_field, now)
        return True
    return False
