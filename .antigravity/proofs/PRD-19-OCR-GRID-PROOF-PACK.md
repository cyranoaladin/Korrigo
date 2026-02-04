# PRD-19: Grid-Based OCR Proof Pack

**Date:** 2026-02-04
**Status:** ✅ IMPLEMENTATION COMPLETE
**Author:** Korrigo Team

---

## Executive Summary

This document provides proof of the PRD-19 Grid-Based OCR implementation for CMEN v2 headers. The system enables automatic student identification from handwritten grid cells without QR codes.

### Key Achievements

| Metric | Value |
|--------|-------|
| Unit Tests | 49/49 PASSED |
| Grid OCR Tests | 33/33 PASSED |
| Auto-ID Tests | 16/16 PASSED |
| Code Coverage | Core modules covered |

---

## 1. Implementation Overview

### 1.1 Core Modules Created

| Module | Purpose | Lines |
|--------|---------|-------|
| `grid_ocr.py` | Grid-based OCR extraction | ~800 |
| `auto_identification.py` | Chunking + Copy creation | ~500 |
| `test_grid_ocr.py` | Unit tests for OCR | ~400 |
| `test_auto_identification.py` | Unit tests for auto-ID | ~400 |

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTO-IDENTIFICATION FLOW                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PDF Batch ──► A3→A4 Split ──► Header Detection ──► Chunking │
│                                       │                      │
│                                       ▼                      │
│                              ┌─────────────────┐             │
│                              │  GridOCRService │             │
│                              ├─────────────────┤             │
│                              │ • Preprocessing │             │
│                              │ • Grid Removal  │             │
│                              │ • Cell Segment  │             │
│                              │ • Char Recogn   │             │
│                              └────────┬────────┘             │
│                                       │                      │
│                                       ▼                      │
│                              ┌─────────────────┐             │
│                              │  CSV Matching   │             │
│                              │  (Closed-World) │             │
│                              └────────┬────────┘             │
│                                       │                      │
│                    ┌──────────────────┼──────────────────┐   │
│                    ▼                  ▼                  ▼   │
│              AUTO_MATCH        AMBIGUOUS_OCR        NO_MATCH │
│                    │                  │                  │   │
│                    ▼                  ▼                  ▼   │
│              Copy READY         Copy STAGING       Copy STAGING│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Test Results

### 2.1 Grid OCR Tests (33/33 PASSED)

```
TestGridLineRemoval:
  ✓ test_grid_line_removal_preserves_content
  ✓ test_grid_line_removal_removes_horizontal_lines
  ✓ test_grid_line_removal_removes_vertical_lines

TestCellSegmentation:
  ✓ test_cell_segmentation_count_geometric
  ✓ test_cell_segmentation_sorted_left_to_right
  ✓ test_cell_segmentation_no_overlap
  ✓ test_cell_segmentation_handles_empty_image

TestCharacterRecognition:
  ✓ test_empty_cell_detection
  ✓ test_cell_with_content_not_empty
  ✓ test_date_field_uses_digit_whitelist
  ✓ test_name_field_uses_letter_whitelist

TestDateStrictness:
  ✓ test_valid_date_format
  ✓ test_invalid_day_rejected
  ✓ test_invalid_month_rejected
  ✓ test_future_year_rejected
  ✓ test_dob_score_exact_match
  ✓ test_dob_score_one_digit_error
  ✓ test_dob_score_two_digit_errors
  ✓ test_dob_score_completely_different

TestCSVMatchingStrictMargin:
  ✓ test_no_auto_assign_when_ambiguous
  ✓ test_auto_assign_with_clear_margin
  ✓ test_no_match_when_below_threshold
  ✓ test_margin_calculation
  ✓ test_ocr_fail_returns_ocr_fail_status
  ✓ test_empty_students_returns_no_match

TestNormalization:
  ✓ test_normalize_removes_accents
  ✓ test_normalize_handles_hyphens
  ✓ test_normalize_handles_apostrophes
  ✓ test_normalize_uppercase
  ✓ test_normalize_compacts_spaces

TestIntegration:
  ✓ test_extract_header_returns_result
  ✓ test_extract_header_status_values
  ✓ test_full_pipeline_with_matching
```

### 2.2 Auto-Identification Tests (16/16 PASSED)

```
TestChunking:
  ✓ test_chunking_creates_correct_chunks
  ✓ test_chunking_handles_single_chunk
  ✓ test_chunking_handles_empty_pages

TestPageCountInvariant:
  ✓ test_valid_block_multiple_of_4
  ✓ test_valid_block_8_pages
  ✓ test_invalid_block_3_pages
  ✓ test_invalid_block_5_pages
  ✓ test_invalid_block_flagged_in_result

TestCopyUniqueness:
  ✓ test_unique_copy_constraint
  ✓ test_multi_sheet_fusion

TestConcurrentAccess:
  ✓ test_select_for_update_used

TestCSVLoading:
  ✓ test_load_csv_semicolon_delimiter
  ✓ test_load_csv_comma_delimiter
  ✓ test_load_csv_handles_bom

TestIntegration:
  ✓ test_full_workflow_dry_run
  ✓ test_ambiguous_ocr_flagged
```

---

## 3. Key Invariants Enforced

### 3.1 Page Count Invariant

```python
# Each student block must have pages as multiple of 4
@property
def is_valid_block(self) -> bool:
    return self.page_count > 0 and self.page_count % 4 == 0
```

**Test:** `test_invalid_block_flagged_in_result` ✅

### 3.2 Unique Copy Per Student Per Exam

```python
# Anti-duplicate with select_for_update
existing_copy = Copy.objects.select_for_update().filter(
    exam=exam,
    student=student
).first()
```

**Test:** `test_unique_copy_constraint` ✅

### 3.3 No Silent False Matches

```python
# Strict thresholds
THRESHOLD_STRICT = 0.75  # Minimum score for auto-match
MARGIN_STRICT = 0.10     # Minimum margin between best and second-best

# DOB must be very close
if best.dob_score >= 0.9:
    status = "AUTO_MATCH"
else:
    status = "AMBIGUOUS_OCR"
```

**Test:** `test_no_auto_assign_when_ambiguous` ✅

### 3.4 Scoring Weights (DOB Priority)

```python
WEIGHT_DOB = 0.55       # Date of birth (most important)
WEIGHT_NAME = 0.25      # Last name
WEIGHT_FIRSTNAME = 0.20 # First name
```

**Test:** `test_dob_score_exact_match`, `test_dob_score_one_digit_error` ✅

---

## 4. Image Processing Pipeline

### 4.1 Preprocessing Steps

1. **Deskew** - Correct slight rotation using Hough transform
2. **CLAHE** - Local contrast enhancement
3. **Adaptive Binarization** - Handle variable lighting
4. **Grid Line Removal** - Morphological operations
5. **Denoising** - Light cleanup without destroying handwriting

### 4.2 Grid Line Removal Algorithm

```python
def _remove_grid_lines(self, binary: np.ndarray) -> np.ndarray:
    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    
    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    
    # Combine and subtract
    grid_lines = cv2.add(horizontal_lines, vertical_lines)
    result = cv2.subtract(binary, grid_lines)
    
    return result
```

**Test:** `test_grid_line_removal_preserves_content` ✅

---

## 5. Matching Algorithm

### 5.1 Normalization (Consistent OCR vs CSV)

```python
def _normalize_for_match(self, text: str) -> str:
    # Uppercase
    text = text.upper()
    # Remove accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Remove hyphens and apostrophes
    text = re.sub(r"[-']", ' ', text)
    # Keep only A-Z and space
    text = re.sub(r'[^A-Z ]', '', text)
    # Compact spaces
    text = ' '.join(text.split())
    return text.strip()
```

**Test:** `test_normalize_removes_accents`, `test_normalize_handles_hyphens` ✅

### 5.2 DOB Strictness

```python
def _calculate_dob_score(self, ocr_dob: str, csv_dob: str) -> float:
    if ocr_dob == csv_dob:
        return 1.0
    
    # Allow 1 digit error
    if len(ocr_dob) == len(csv_dob) == 8:
        errors = sum(1 for a, b in zip(ocr_dob, csv_dob) if a != b)
        if errors == 1:
            return 0.9
        elif errors == 2:
            return 0.7
    
    return self._jaro_winkler(ocr_dob, csv_dob) * 0.5
```

**Test:** `test_dob_score_one_digit_error` ✅

---

## 6. Status Codes

| Status | Description | Action |
|--------|-------------|--------|
| `AUTO_MATCH` | High confidence match | Copy → READY |
| `AMBIGUOUS_OCR` | Multiple close candidates | Copy → STAGING (review) |
| `INVALID_BLOCK` | Page count not multiple of 4 | Copy → STAGING + error |
| `OCR_FAIL` | OCR extraction failed | Copy → STAGING + error |
| `NO_MATCH` | No matching student in CSV | Copy → STAGING |

---

## 7. Files Modified/Created

### New Files
- `backend/processing/services/grid_ocr.py`
- `backend/processing/services/auto_identification.py`
- `backend/processing/tests/test_grid_ocr.py`
- `backend/processing/tests/test_auto_identification.py`

### Modified Files
- `backend/pytest.ini` (added `ocr` marker)

---

## 8. Commits

```
53a0c03 feat(PRD-19): Implement grid-based OCR for CMEN v2 headers
425840f feat(PRD-19): Add auto-identification service with chunking and anti-duplicates
```

---

## 9. Next Steps for Production

1. **Docker Validation** - Run full workflow in local-prod environment
2. **Real Data Testing** - Test with actual CMEN v2 scans
3. **Performance Tuning** - Optimize OCR engine selection
4. **Monitoring** - Add metrics for auto_identified_count, ambiguous_count, etc.

---

## 10. Conclusion

The PRD-19 Grid-Based OCR implementation is **complete** with:

- ✅ 49/49 unit tests passing
- ✅ Grid line removal without destroying handwriting
- ✅ Cell segmentation with geometric fallback
- ✅ Character-level recognition with whitelists
- ✅ Strict CSV matching with DOB priority
- ✅ No silent false matches (AMBIGUOUS_OCR for uncertain cases)
- ✅ Page count invariant (multiple of 4)
- ✅ Anti-duplicate protection with select_for_update
- ✅ Multi-sheet fusion for same student

**The system is ready for Docker local-prod validation.**
