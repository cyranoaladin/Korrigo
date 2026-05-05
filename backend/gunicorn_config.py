import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# BUG-11 FIX: utiliser gthread pour absorber les I/O bloquants (PDF, BCrypt)
# sans monopoliser un worker sync entier. Avec sync workers, une requête PDF
# de 30s bloquerait le worker pour tous les élèves suivants.
worker_class = 'gthread'
workers = int(os.environ.get('GUNICORN_WORKERS', '4'))
threads = 4  # Augmenté : chaque worker gère 4 requêtes concurrentes

# Recycle workers after N requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Timeout set to 120s to allow for heavy PDF flattening operations
timeout = 120
forwarded_allow_ips = os.environ.get('GUNICORN_FORWARDED_IPS', '*')
