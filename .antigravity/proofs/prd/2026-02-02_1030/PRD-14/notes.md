# PRD-14: Workflow Métier Complet

## Status: PASS

## API Endpoints Verified

### Admin Flow
1. **Login**: `POST /api/login/` → 200 OK
2. **Exams list**: `GET /api/exams/` → 2 exams returned
3. **Copies list**: `GET /api/copies/` → 5 copies returned

### Student Flow
1. **Login**: `POST /api/students/login/` with email+last_name → 200 OK
2. **Copies list**: `GET /api/students/copies/` → Returns only GRADED copies for student

### Workflow States Verified
- GRADED copies visible to students
- LOCKED copies filtered from student view
- Exam data includes correctors assignment
- Copy data includes status, student assignment, final PDF URL

## Conclusion
Core workflow endpoints are functional. Student portal correctly filters copies by status and ownership.
