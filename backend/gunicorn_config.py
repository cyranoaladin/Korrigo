import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# BUG-11 FIX: utiliser gthread pour absorber les I/O bloquants (PDF, BCrypt)
# sans monopoliser un worker sync entier. Avec sync workers, une requête PDF
# de 30s bloquerait le worker pour tous les élèves suivants.
worker_class = 'gthread'
workers = multiprocessing.cpu_count() * 2 + 1
threads = 4  # Augmenté : chaque worker gère 4 requêtes concurrentes

# Timeout set to 120s to allow for heavy PDF flattening operations
timeout = 120
forwarded_allow_ips = os.environ.get('GUNICORN_FORWARDED_IPS', '*')
