import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 4)))
threads = 2
# Timeout set to 120s to allow for heavy PDF flattening operations
timeout = 120
forwarded_allow_ips = '*'

# ---------------------------------------------------------------------------
# Production hardening
# ---------------------------------------------------------------------------

# Process naming: workers are visible as "korrigo-gunicorn" in `ps aux`
proc_name = "korrigo-gunicorn"

# Structured access logging to stdout (captured by Docker)
accesslog = "-"
errorlog = "-"
access_log_format = '{"remote_addr":"%(h)s","request":"%(r)s","status":"%(s)s","response_length":"%(b)s","response_time_us":"%(D)s","referer":"%(f)s","user_agent":"%(a)s"}'

# Preload app: share memory across workers via copy-on-write after fork.
# Django handles post-fork DB connection cleanup automatically.
preload_app = True

# Worker recycling: prevent memory leaks over time
max_requests = 1000
max_requests_jitter = 50

# Graceful shutdown timeout
graceful_timeout = 30

# Use /dev/shm for worker heartbeat tmpfiles (faster than disk in Docker)
worker_tmp_dir = "/dev/shm"
