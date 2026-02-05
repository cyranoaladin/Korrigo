# Structured Logging Guide - Korrigo

**Phase 4: Enhanced Observability with Structlog**

## Overview

Korrigo now uses **structlog** for structured JSON logging, providing better observability, searchability, and debugging capabilities.

### Benefits

- **Searchable**: Query logs by any field (copy_id, exam_id, user_id, etc.)
- **Contextual**: Bind context once, use in all subsequent logs
- **Consistent**: Standardized log format across all components
- **Production-Ready**: JSON output in production, pretty console in development

---

## Quick Start

### Basic Usage

```python
from core.utils.structlog_helper import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("copy_graded", copy_id=copy.id, score=18.5)

# Output (production):
# {"timestamp": "2026-02-05T10:30:45.123Z", "level": "info", "logger": "grading.views",
#  "event": "copy_graded", "copy_id": "abc-123", "score": 18.5}
```

### With Context Binding

```python
# Bind context once
logger = logger.bind(
    exam_id=exam.id,
    corrector_id=request.user.id
)

# All subsequent logs include bound context
logger.info("grading_started")
logger.info("annotation_created", annotation_id=annotation.id)
logger.info("grading_completed", duration_ms=1234.5)

# Each log automatically includes exam_id and corrector_id
```

---

## Common Patterns

### 1. API Request Logging

```python
from core.utils.structlog_helper import get_logger, log_api_request

def my_view(request):
    logger = get_logger(__name__)
    logger = log_api_request(
        logger,
        request.method,
        request.path,
        user_id=request.user.id if request.user.is_authenticated else None
    )

    # Process request...

    logger.info("request_completed", status_code=200, duration_ms=123.4)
```

### 2. Celery Task Logging

```python
from core.utils.structlog_helper import get_logger, log_task_start, log_task_end
from celery import shared_task
import time

@shared_task(bind=True)
def async_flatten_copy(self, copy_id):
    logger = get_logger(__name__)
    logger = log_task_start(logger, "async_flatten_copy",
                           task_id=self.request.id,
                           copy_id=copy_id)

    start_time = time.time()

    try:
        # Do work...
        copy = Copy.objects.get(id=copy_id)
        flattener.flatten_copy(copy)

        duration_ms = (time.time() - start_time) * 1000
        log_task_end(logger, "async_flatten_copy", success=True, duration_ms=duration_ms)

        return {"status": "success", "copy_id": str(copy_id)}

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.exception("task_exception", duration_ms=duration_ms)
        log_task_end(logger, "async_flatten_copy", success=False,
                    duration_ms=duration_ms, error=str(e))
        raise
```

### 3. Security Event Logging

```python
from core.utils.structlog_helper import get_logger, log_security_event

def login_view(request):
    logger = get_logger(__name__)

    username = request.data.get('username')
    user = authenticate(request, username=username, password=password)

    if user:
        log_security_event(
            logger,
            "login_success",
            user_id=user.id,
            ip_address=request.META.get('REMOTE_ADDR'),
            success=True,
            username=username
        )
    else:
        log_security_event(
            logger,
            "login_failure",
            ip_address=request.META.get('REMOTE_ADDR'),
            success=False,
            username=username
        )
```

### 4. Database Operations

```python
from core.utils.structlog_helper import get_logger, log_database_operation
import time

def bulk_create_students(student_data):
    logger = get_logger(__name__)

    start_time = time.time()
    students = Student.objects.bulk_create([
        Student(**data) for data in student_data
    ])
    duration_ms = (time.time() - start_time) * 1000

    log_database_operation(
        logger,
        "bulk_create",
        "Student",
        count=len(students),
        duration_ms=duration_ms
    )

    return students
```

### 5. Performance Metrics

```python
from core.utils.structlog_helper import get_logger, log_performance_metric
import time

def process_ocr(copy):
    logger = get_logger(__name__)

    start_time = time.time()
    result = perform_ocr(copy)
    duration_ms = (time.time() - start_time) * 1000

    log_performance_metric(
        logger,
        "ocr_duration",
        duration_ms,
        unit="ms",
        copy_id=copy.id,
        engine="tesseract"
    )

    return result
```

---

## Migration from Old Logging

### Before (Python logging)

```python
import logging

logger = logging.getLogger(__name__)
logger.info(f"Copy {copy.id} graded with score {score} by user {user.id}")
```

**Problems**:
- String formatting makes it hard to search
- No structured data
- Context scattered across log message

### After (Structlog)

```python
from core.utils.structlog_helper import get_logger

logger = get_logger(__name__)
logger.info("copy_graded", copy_id=copy.id, score=score, corrector_id=user.id)
```

**Benefits**:
- Searchable by copy_id, score, corrector_id
- Consistent event naming
- Machine-parseable JSON output

---

## Log Levels

Use appropriate log levels:

| Level | When to Use | Example |
|-------|-------------|---------|
| **debug** | Development debugging, verbose info | `logger.debug("query_executed", sql=query, rows=count)` |
| **info** | Normal operations, successful actions | `logger.info("copy_graded", copy_id=id)` |
| **warning** | Unexpected but handled situations | `logger.warning("retry_needed", attempt=3)` |
| **error** | Errors that need attention | `logger.error("ocr_failed", error=str(e))` |
| **exception** | Exceptions with full traceback | `logger.exception("unhandled_error")` |

---

## Best Practices

### ✅ DO

```python
# Use structured fields
logger.info("copy_exported", copy_id=copy.id, format="pdf", size_bytes=file_size)

# Use consistent event names
logger.info("task_started")
logger.info("task_completed")

# Bind context early
logger = logger.bind(exam_id=exam.id)
logger.info("exam_created")
logger.info("copies_imported", count=100)

# Log performance metrics
logger.info("query_executed", duration_ms=123.4, rows=50)
```

### ❌ DON'T

```python
# Don't use f-strings
logger.info(f"Copy {copy_id} exported")  # NOT SEARCHABLE

# Don't log sensitive data
logger.info("user_login", password=password)  # SECURITY ISSUE

# Don't use inconsistent naming
logger.info("TaskStarted")  # Should be "task_started"
logger.info("TASK-COMPLETE")  # Should be "task_completed"

# Don't log huge objects
logger.info("data", full_object=exam)  # Use specific fields instead
```

---

## Searching Logs

### In Development (Console)

Logs are pretty-printed to console with colors.

### In Production (JSON)

Use `jq` to search JSON logs:

```bash
# Find all copy_graded events
docker-compose logs backend | grep copy_graded | jq '.'

# Find all errors
docker-compose logs backend | jq 'select(.level == "error")'

# Find logs for specific copy
docker-compose logs backend | jq 'select(.copy_id == "abc-123")'

# Find slow queries (>1 second)
docker-compose logs backend | jq 'select(.duration_ms > 1000)'

# Count events by type
docker-compose logs backend | jq -r '.event' | sort | uniq -c
```

### With Log Aggregation (Sentry, Grafana Loki, etc.)

Structured logs can be:
- Searched by any field
- Filtered by time range
- Aggregated for metrics
- Alerted on specific patterns

---

## Integration with Sentry

Structlog context is automatically captured by Sentry:

```python
logger = get_logger(__name__)
logger = logger.bind(exam_id=exam.id, user_id=user.id)

try:
    risky_operation()
except Exception as e:
    logger.exception("operation_failed")
    # Sentry will capture exam_id and user_id in event context
```

---

## Examples by Component

### Grading

```python
from core.utils.structlog_helper import get_logger

logger = get_logger(__name__)

# When starting grading
logger = logger.bind(copy_id=copy.id, exam_id=copy.exam_id, corrector_id=request.user.id)
logger.info("grading_started")

# Each annotation
logger.info("annotation_created", annotation_id=annotation.id, score=annotation.score)

# Final grade
logger.info("copy_graded", total_score=final_score, duration_ms=elapsed_time)
```

### OCR

```python
from core.utils.structlog_helper import get_logger, log_performance_metric

logger = get_logger(__name__)
logger = logger.bind(copy_id=copy.id)

logger.info("ocr_started", engine="tesseract")

start = time.time()
result = ocr_engine.process(image)
duration_ms = (time.time() - start) * 1000

log_performance_metric(logger, "ocr_duration", duration_ms, unit="ms")

logger.info("ocr_completed", confidence=result.confidence, text_length=len(result.text))
```

### Export

```python
from core.utils.structlog_helper import get_logger

logger = get_logger(__name__)
logger = logger.bind(exam_id=exam.id)

logger.info("export_started", copies_count=copies.count())

for i, copy in enumerate(copies):
    logger.info("copy_exporting", copy_id=copy.id, progress=f"{i+1}/{copies.count()}")
    export_copy(copy)

logger.info("export_completed", copies_count=copies.count(), duration_ms=elapsed_time)
```

---

## Configuration

Structlog is configured in `backend/core/settings.py`:

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # Merge context from contextvars
        structlog.stdlib.filter_by_level,  # Filter by log level
        structlog.stdlib.add_logger_name,  # Add logger name
        structlog.stdlib.add_log_level,  # Add log level
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamps
        structlog.processors.StackInfoRenderer(),  # Stack traces
        structlog.processors.format_exc_info,  # Format exceptions
        structlog.processors.UnicodeDecoder(),  # Handle unicode
        # JSON in production, pretty console in development
        structlog.processors.JSONRenderer() if not DEBUG else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

---

## Troubleshooting

### Logs not appearing

1. Check log level in settings:
   ```python
   DJANGO_LOG_LEVEL=INFO  # In .env
   ```

2. Check logger is configured:
   ```python
   import structlog
   logger = structlog.get_logger(__name__)
   logger.info("test")  # Should appear in console
   ```

### JSON not formatted

Make sure `DEBUG=False` in production (JSON output) or `DEBUG=True` in development (pretty console).

### Missing context

Make sure to bind context:
```python
logger = logger.bind(copy_id=copy.id)  # Bind first
logger.info("event")  # Context included
```

---

## Next Steps

1. ✅ Migrate critical endpoints to use structlog
2. ✅ Add performance metrics logging
3. ✅ Integrate with Grafana Loki for log aggregation
4. ✅ Create dashboards based on structured logs
5. ✅ Set up alerts on specific log patterns

---

**Status**: ✅ Structlog configured and ready to use
**Next**: Start migrating existing logging calls to structured format
