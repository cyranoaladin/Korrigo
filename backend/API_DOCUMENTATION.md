# API Documentation - Korrigo PMF

## Exam Upload API

### Endpoints

#### 1. Create Exam with Upload Mode

**Endpoint:** `POST /api/exams/upload/`

**Description:** Creates a new exam with support for two upload modes:
- **BATCH_A3**: Upload a single PDF containing multiple student copies (A3 scans) that will be automatically split
- **INDIVIDUAL_A4**: Upload multiple pre-split individual PDF files (A4), one per student

**Authentication:** Required (Teacher or Admin)

**Rate Limiting:** 20 requests/hour

**Request Format:** `multipart/form-data`

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Exam name |
| `date` | date (YYYY-MM-DD) | Yes | Exam date |
| `upload_mode` | string | No | Upload mode: `BATCH_A3` (default) or `INDIVIDUAL_A4` |
| `pdf_source` | file (PDF) | Conditional | Required if `upload_mode=BATCH_A3`. Max 50MB, 500 pages max |
| `pages_per_booklet` | integer | Conditional | Required if `upload_mode=BATCH_A3`. Number of pages per student copy |
| `students_csv` | file (CSV) | No | Optional CSV file containing student list |
| `grading_structure` | JSON | No | Optional grading structure/barème |

**Validation Rules:**

1. **BATCH_A3 Mode:**
   - `pdf_source` is **required**
   - `pages_per_booklet` is **required**
   - PDF must be valid, non-empty, under 50MB, max 500 pages
   - MIME type must be `application/pdf`

2. **INDIVIDUAL_A4 Mode:**
   - `pdf_source` is **not required** (and will be ignored if provided)
   - Exam is created in a state ready to receive individual PDF uploads

**Response (Success - 201 Created):**

```json
{
  "id": "uuid",
  "name": "Bac Blanc Maths 2026",
  "date": "2026-01-15",
  "upload_mode": "BATCH_A3",
  "pdf_source": "https://example.com/media/exams/source/file.pdf",
  "students_csv": "https://example.com/media/exams/csv/students.csv",
  "created_at": "2026-02-10T22:00:00Z",
  "message": "Examen créé avec succès. 25 copies créées."
}
```

For INDIVIDUAL_A4 mode, response includes:

```json
{
  "id": "uuid",
  "name": "Exam Individual",
  "date": "2026-01-15",
  "upload_mode": "INDIVIDUAL_A4",
  "upload_endpoint": "/api/exams/{exam_id}/upload-individual-pdfs/",
  "created_at": "2026-02-10T22:00:00Z",
  "message": "Examen créé. Utilisez l'endpoint upload_endpoint pour uploader les PDFs individuels."
}
```

**Error Responses:**

| Status Code | Condition | Response Example |
|-------------|-----------|------------------|
| 400 Bad Request | Missing required fields | `{"error": "pdf_source est requis en mode BATCH_A3"}` |
| 400 Bad Request | Invalid PDF | `{"error": "Le fichier n'est pas un PDF valide"}` |
| 400 Bad Request | Empty PDF | `{"error": "Le fichier PDF est vide"}` |
| 413 Payload Too Large | PDF > 50MB | `{"error": "Le fichier PDF est trop volumineux. Taille maximale : 50 MB"}` |
| 400 Bad Request | Too many pages | `{"error": "Le PDF contient trop de pages (max 500)"}` |
| 401 Unauthorized | Not authenticated | `{"detail": "Authentication credentials were not provided"}` |
| 403 Forbidden | Not Teacher/Admin | `{"detail": "You do not have permission to perform this action"}` |

---

#### 2. Upload Individual PDFs

**Endpoint:** `POST /api/exams/{exam_id}/upload-individual-pdfs/`

**Description:** Uploads multiple individual PDF files for an exam in `INDIVIDUAL_A4` mode. Each PDF represents one student's copy.

**Authentication:** Required (Teacher or Admin)

**Rate Limiting:** 50 requests/hour

**Request Format:** `multipart/form-data`

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pdf_files` | file[] (PDF) | Yes | Array of PDF files. Max 100 files per request. Each file max 50MB |

**Validation Rules:**

1. Exam must be in `INDIVIDUAL_A4` mode
2. At least 1 PDF file must be provided
3. Maximum 100 PDF files per request
4. Each PDF must be valid, non-empty, under 50MB
5. MIME type validation for each file

**Response (Success - 201 Created):**

```json
{
  "message": "3 fichiers PDF uploadés avec succès",
  "uploaded_files": [
    {
      "filename": "martin_jean.pdf",
      "student_identifier": "martin_jean",
      "exam_pdf_id": "uuid",
      "copy_id": "uuid",
      "status": "STAGING"
    },
    {
      "filename": "dupont_marie.pdf",
      "student_identifier": "dupont_marie",
      "exam_pdf_id": "uuid",
      "copy_id": "uuid",
      "status": "STAGING"
    },
    {
      "filename": "bernard_paul.pdf",
      "student_identifier": "bernard_paul",
      "exam_pdf_id": "uuid",
      "copy_id": "uuid",
      "status": "STAGING"
    }
  ],
  "total_copies": 3
}
```

**Error Responses:**

| Status Code | Condition | Response Example |
|-------------|-----------|------------------|
| 400 Bad Request | No files provided | `{"error": "Le champ 'pdf_files' est requis"}` |
| 400 Bad Request | Too many files | `{"error": "Maximum 100 fichiers par requête"}` |
| 400 Bad Request | Exam not in INDIVIDUAL_A4 mode | `{"error": "Cet endpoint n'est disponible que pour les examens en mode INDIVIDUAL_A4"}` |
| 400 Bad Request | Invalid PDF | `{"error": "Erreur avec file.pdf: Le fichier n'est pas un PDF valide"}` |
| 413 Payload Too Large | File > 50MB | `{"error": "Erreur avec file.pdf: Le fichier est trop volumineux"}` |
| 404 Not Found | Exam doesn't exist | `{"detail": "Not found."}` |

---

## Data Models

### Exam Model

```python
{
  "id": UUID,
  "name": string,
  "date": date,
  "upload_mode": "BATCH_A3" | "INDIVIDUAL_A4",  # NEW FIELD
  "pdf_source": FileField (nullable),  # CHANGED: Now nullable
  "students_csv": FileField (nullable),  # NEW FIELD
  "grading_structure": JSON,
  "correctors": [User],
  "created_at": datetime,
  "updated_at": datetime
}
```

### ExamPDF Model (NEW)

```python
{
  "id": UUID,
  "exam": ForeignKey(Exam),
  "pdf_file": FileField,  # Stored in media/exams/individual/
  "student_identifier": string,  # Extracted from filename
  "uploaded_at": datetime
}
```

### Copy Model

```python
{
  "id": UUID,
  "exam": ForeignKey(Exam),
  "anonymous_id": string (unique),
  "pdf_source": FileField (nullable),  # CHANGED: Now nullable
  "status": "STAGING" | "READY" | "LOCKED" | "GRADING_IN_PROGRESS" | "GRADED",
  "student": ForeignKey(Student, nullable),
  "is_identified": boolean,
  "assigned_corrector": ForeignKey(User, nullable),
  ...
}
```

---

## Migration Guide

### Breaking Changes

1. **`Exam.pdf_source` is now optional (nullable)**
   - **Impact:** Code that assumes `exam.pdf_source` is always present may fail
   - **Fix:** Add null checks before accessing `exam.pdf_source`:
     ```python
     if exam.pdf_source:
         pdf_path = exam.pdf_source.path
     ```

2. **New upload mode field**
   - **Impact:** Existing exams will have `upload_mode=NULL` until migration runs
   - **Fix:** Run migrations to set default `upload_mode='BATCH_A3'` for existing exams

### Migration Steps

1. Run database migrations:
   ```bash
   python manage.py migrate
   ```

2. Update frontend code to handle new `upload_mode` field

3. Test both upload modes thoroughly

---

## Security Considerations

1. **File Validation:** All PDF uploads go through 5-layer validation:
   - Extension check (.pdf only)
   - Size check (max 50MB)
   - Empty file check
   - MIME type verification (using python-magic)
   - PDF integrity check (using PyMuPDF, max 500 pages)

2. **Path Traversal Protection:** Filenames are sanitized to prevent directory traversal attacks

3. **Rate Limiting:** Upload endpoints are rate-limited to prevent abuse

4. **Authentication:** All upload endpoints require Teacher or Admin role

5. **Transaction Atomicity:** All upload operations are wrapped in database transactions to prevent partial state

---

## Examples

### Example 1: Upload Batch A3 Exam

```bash
curl -X POST http://localhost:8000/api/exams/upload/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "name=Bac Blanc Maths 2026" \
  -F "date=2026-01-15" \
  -F "upload_mode=BATCH_A3" \
  -F "pages_per_booklet=4" \
  -F "pdf_source=@exam_scan.pdf"
```

### Example 2: Create Individual A4 Exam and Upload PDFs

Step 1: Create exam
```bash
curl -X POST http://localhost:8000/api/exams/upload/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "name=Exam Individual" \
  -F "date=2026-01-15" \
  -F "upload_mode=INDIVIDUAL_A4"
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "upload_endpoint": "/api/exams/550e8400-e29b-41d4-a716-446655440000/upload-individual-pdfs/"
}
```

Step 2: Upload individual PDFs
```bash
curl -X POST http://localhost:8000/api/exams/550e8400-e29b-41d4-a716-446655440000/upload-individual-pdfs/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "pdf_files=@martin_jean.pdf" \
  -F "pdf_files=@dupont_marie.pdf" \
  -F "pdf_files=@bernard_paul.pdf"
```

---

## Testing

Run comprehensive tests:
```bash
# Run all upload tests
pytest backend/exams/tests/test_upload_endpoint.py -v

# Run specific test classes
pytest backend/exams/tests/test_upload_endpoint.py::TestUploadModes -v
pytest backend/exams/tests/test_upload_endpoint.py::TestIndividualPDFUpload -v
pytest backend/exams/tests/test_upload_endpoint.py::TestIndividualModeValidation -v
pytest backend/exams/tests/test_upload_endpoint.py::TestIndividualModeAtomicity -v
```

Coverage: 39 tests for upload functionality (validation, atomicity, authentication, security, modes)

