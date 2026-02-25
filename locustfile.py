import random
from locust import HttpUser, task, between, events

class CampusProUser(HttpUser):
    # Wait time between tasks (1-3 seconds as requested)
    wait_time = between(1, 3)
    
    # Store user credentials (assuming some exist or using the default admin for testing)
    # In a real scenario, you'd load this from a CSV
    email = "student@gmail.com" 
    password = "password123"

    def on_start(self):
        """ Runs when a simulated user starts (Login simulation) """
        self.login()

    def login(self):
        """ Simulate POST /login """
        with self.client.post("/login", {
            "username": self.email,
            "password": self.password
        }, catch_responses=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to login with status: {response.status_code}")

    @task(3)
    def access_dashboard(self):
        """ Simulate GET / (Student Dashboard) """
        self.client.get("/")

    @task(1)
    def access_admin(self):
        """ Simulate GET /admin (Checking for restricted access or admin performance) """
        # Students will likely be redirected or get a flash message
        self.client.get("/admin")

    @task(2)
    def access_notices(self):
        """ Simulate seeing notices """
        self.client.get("/messages")

# To run this:
# 1. Install locust: pip install locust
# 2. Run: locust -f locustfile.py --host http://127.0.0.1:5000
# 3. Open browser at: http://localhost:8089 to start the test (5000 users)
