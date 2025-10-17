import time
import os
import sys

print("Worker started - this is a placeholder", flush=True)
print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'not set')}", flush=True)

# Keep the worker running
while True:
    time.sleep(60)
    print("Worker is alive...", flush=True)