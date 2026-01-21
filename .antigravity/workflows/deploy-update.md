---
description: Updates the Docker environment safely.
---

1.  Check `docker-compose.yml` for consistency.
2.  Run migration commands (`python manage.py migrate`) inside the container context.
3.  Rebuild containers if dependencies changed.
// turbo-all
