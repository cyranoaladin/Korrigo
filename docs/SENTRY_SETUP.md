# Sentry Error Tracking Setup Guide

**Phase 4: Error Tracking and Monitoring**

## Overview

Sentry provides real-time error tracking, performance monitoring, and alerting for the Korrigo application. This guide explains how to set up and configure Sentry.

---

## 1. Create Sentry Account

1. Go to https://sentry.io/signup/
2. Create a free account (includes 5,000 errors/month)
3. Create a new project:
   - Platform: **Django**
   - Project name: **Korrigo**

---

## 2. Get Your DSN

After creating the project:

1. Navigate to **Settings → Projects → Korrigo → Client Keys (DSN)**
2. Copy the DSN (looks like):
   ```
   https://abc123def456@o123456.ingest.sentry.io/789012
   ```

---

## 3. Configure Korrigo

Add the DSN to your `.env` file:

```bash
# Phase 4: Error Tracking and Monitoring
SENTRY_DSN=https://abc123def456@o123456.ingest.sentry.io/789012
GIT_COMMIT_SHA=01c1541  # Optional: Current git commit
```

---

## 4. Install Dependencies

The Sentry SDK is already added to `requirements.txt`. Rebuild your Docker containers:

```bash
docker-compose -f infra/docker/docker-compose.local-prod.yml down
docker-compose -f infra/docker/docker-compose.local-prod.yml build backend
docker-compose -f infra/docker/docker-compose.local-prod.yml up -d
```

---

## 5. Test Error Tracking

### Test 1: Trigger a Test Error

```bash
# From Django shell
docker-compose -f infra/docker/docker-compose.local-prod.yml exec backend python manage.py shell

# In the shell:
from sentry_sdk import capture_message
capture_message("Sentry is configured correctly!", level="info")
```

Check your Sentry dashboard - you should see the message.

### Test 2: Trigger an Exception

```python
# In Django shell:
def trigger_error():
    division_by_zero = 1 / 0

trigger_error()
```

Check Sentry - you should see a `ZeroDivisionError`.

---

## 6. Features Enabled

### Automatic Error Tracking
- Unhandled exceptions
- Database errors
- Request failures
- Celery task failures

### Performance Monitoring
- API endpoint response times
- Database query performance
- Celery task duration
- Redis operation timing

### Integrations
- **Django**: HTTP request tracking, middleware errors
- **Celery**: Task failures, retries, timeouts
- **Redis**: Cache operation monitoring

---

## 7. Privacy & Security

Sentry is configured with privacy in mind:

- **PII disabled**: `send_default_pii=False`
- **Sensitive data filtering**: Passwords, tokens, secrets are filtered out
- **Environment tracking**: Production vs development separation
- **Sampling**: 10% of transactions sampled in production (reduces noise)

---

## 8. Sentry Dashboard

### Key Sections

**Issues**: List of errors grouped by type
- Click on an issue to see stack trace, user context, breadcrumbs

**Performance**: Transaction monitoring
- See which API endpoints are slow
- Identify database query bottlenecks

**Releases**: Track errors by deployment
- Set `GIT_COMMIT_SHA` environment variable
- See which commits introduced errors

**Alerts**: Configure notifications
- Email alerts for new issues
- Slack integration available
- PagerDuty for critical errors

---

## 9. Recommended Alerts

Set up these alerts in Sentry dashboard:

1. **Critical Errors**
   - Condition: Any new issue
   - Action: Email to admins
   - Frequency: Immediately

2. **High Error Rate**
   - Condition: >10 errors in 5 minutes
   - Action: Email + Slack
   - Frequency: Once per hour

3. **Performance Degradation**
   - Condition: P95 response time >2 seconds
   - Action: Email to dev team
   - Frequency: Once per day

---

## 10. Best Practices

### Custom Context

Add custom context to Sentry events:

```python
from sentry_sdk import set_context, set_user, set_tag

# In views.py
def some_view(request):
    # Add user context
    set_user({
        "id": request.user.id,
        "username": request.user.username,
        "email": request.user.email
    })

    # Add custom context
    set_context("exam", {
        "exam_id": exam.id,
        "exam_name": exam.name,
        "copies_count": exam.copies.count()
    })

    # Add tags for filtering
    set_tag("exam_type", exam.exam_type)
```

### Breadcrumbs

Breadcrumbs show the sequence of events leading to an error:

```python
from sentry_sdk import add_breadcrumb

add_breadcrumb(
    category='ocr',
    message='Starting OCR processing',
    level='info',
    data={'copy_id': copy.id}
)
```

### Manual Error Reporting

```python
from sentry_sdk import capture_exception, capture_message

try:
    risky_operation()
except Exception as e:
    capture_exception(e)
    # Handle gracefully
```

---

## 11. Cost Management

**Free Tier**: 5,000 errors/month

If you exceed:
1. **Upgrade to paid**: $26/month for 50k errors
2. **Filter noise**: Ignore common errors in Sentry settings
3. **Sampling**: Already configured at 10% for production

---

## 12. Troubleshooting

### Sentry Not Capturing Errors

1. Check DSN is set:
   ```bash
   docker-compose exec backend env | grep SENTRY
   ```

2. Check Sentry is initialized:
   ```python
   import sentry_sdk
   print(sentry_sdk.Hub.current.client)  # Should show <Client object>
   ```

3. Check logs:
   ```bash
   docker-compose logs backend | grep -i sentry
   ```

### Too Many Errors

1. Filter out known issues in Sentry dashboard
2. Add custom `before_send` filters in settings.py
3. Reduce sampling rate

---

## 13. Next Steps

After Sentry is configured:

1. ✅ Monitor dashboard for first 24 hours
2. ✅ Configure alert rules
3. ✅ Set up Slack integration (optional)
4. ✅ Add custom context to critical operations
5. ✅ Document common issues in runbooks

---

## Resources

- Sentry Docs: https://docs.sentry.io/platforms/python/guides/django/
- Django Integration: https://docs.sentry.io/platforms/python/guides/django/
- Celery Integration: https://docs.sentry.io/platforms/python/guides/celery/
- Performance Monitoring: https://docs.sentry.io/product/performance/

---

**Configuration Status**: ✅ Sentry SDK installed and configured
**Next Task**: Add Prometheus metrics for detailed monitoring
