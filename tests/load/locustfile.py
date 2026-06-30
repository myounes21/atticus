import os
import uuid
from locust import HttpUser, task, between, events
import logging

logger = logging.getLogger(__name__)

class AtticusAPIUser(HttpUser):
    wait_time = between(1, 3)
    
    # Use environment variable or default
    host = os.environ.get("ATTICUS_API_URL", "http://localhost:8000")

    def on_start(self):
        # Authenticate and get token
        response = self.client.post("/auth/login", json={
            "email": "demo.admin@atticus.local",
            "password": "DemoPass!123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            
            # Fetch cases to get the Finch Demo Matter case_id
            cases_resp = self.client.get("/cases", headers=self.headers)
            cases_data = cases_resp.json()
            if cases_data and cases_data.get("cases"):
                self.case_id = cases_data["cases"][0]["case_id"]
            else:
                logger.error("No cases found.")
                self.case_id = None
        else:
            logger.error("Login failed.")
            self.token = None
            self.case_id = None

    @task(1)
    def cache_miss_cold_query(self):
        """Simulates a unique question to guarantee a cache miss."""
        if not self.case_id:
            return
            
        # Append a UUID to make the query unique every time
        unique_id = str(uuid.uuid4())[:8]
        query = f"What is the liability mentioned in the contract? ({unique_id})"
        
        self.client.post("/chat", json={
            "case_id": self.case_id,
            "query": query,
            "stream": False 
        }, headers=self.headers, name="Cache Miss (Cold)")

    @task(3)
    def cache_hit_warm_query(self):
        """Simulates a repeated question to hit the semantic cache."""
        if not self.case_id:
            return
            
        # Static query will hit the cache after the first execution
        query = "Who is the plaintiff in this case?"
        
        self.client.post("/chat", json={
            "case_id": self.case_id,
            "query": query,
            "stream": False
        }, headers=self.headers, name="Cache Hit (Warm)")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print the delta between cache hit and cache miss at the end."""
    stats = environment.stats.entries
    
    cold_stats = stats.get(("Cache Miss (Cold)", "POST"))
    warm_stats = stats.get(("Cache Hit (Warm)", "POST"))
    
    print("\n" + "="*50)
    print("CACHE HIT VS MISS LATENCY DELTA (LOCUST RESULTS)")
    print("="*50)
    
    if not cold_stats or not warm_stats or cold_stats.num_requests == 0 or warm_stats.num_requests == 0:
        print("Not enough data to calculate delta. Make sure both tasks run at least once.")
        print("="*50)
        return
        
    def get_percentile(stat_entry, p):
        return stat_entry.get_response_time_percentile(p)
        
    cold_p50 = get_percentile(cold_stats, 0.5)
    cold_p95 = get_percentile(cold_stats, 0.95)
    cold_p99 = get_percentile(cold_stats, 0.99)
    
    warm_p50 = get_percentile(warm_stats, 0.5)
    warm_p95 = get_percentile(warm_stats, 0.95)
    warm_p99 = get_percentile(warm_stats, 0.99)
    
    delta_p50 = cold_p50 - warm_p50
    delta_p95 = cold_p95 - warm_p95
    delta_p99 = cold_p99 - warm_p99
    
    print(f"P50 Latency : Miss={cold_p50:.1f}ms, Hit={warm_p50:.1f}ms (Delta: {delta_p50:.1f}ms)")
    print(f"P95 Latency : Miss={cold_p95:.1f}ms, Hit={warm_p95:.1f}ms (Delta: {delta_p95:.1f}ms)")
    print(f"P99 Latency : Miss={cold_p99:.1f}ms, Hit={warm_p99:.1f}ms (Delta: {delta_p99:.1f}ms)")
    print("="*50)
