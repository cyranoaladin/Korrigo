import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
# Timeout set to 120s to allow for heavy PDF flattening operations
timeout = 120
forwarded_allow_ips = '*'
