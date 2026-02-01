# API Error Contract — Grading

## JSON error shape
All grading workflow and lock endpoints MUST return errors as:

```json
{"detail": "<message>"}
```

No other error key is allowed (`error`, `message`, etc.).

## Exception → HTTP mapping
- `PermissionError` → **403**
- `LockConflictError` → **409**
- `ValueError` / `KeyError` → **400**
- Unexpected exception → **500** with:

```json
{"detail": "An unexpected error occurred. Please contact support."}
```

## Lock endpoints rules
- Missing/invalid token → **403**
- Lock not found or expired → **404**
- Lock owner mismatch / locked by other user → **409**

## Non-goals
DRF serializer validation errors may return structured field-level errors. This contract applies to workflow/lock endpoints when the error originates from the service layer / business rules.
