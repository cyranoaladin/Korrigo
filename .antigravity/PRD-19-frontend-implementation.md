# PRD-19: Frontend Implementation - Multi-layer OCR Identification

## Overview

Implementation of the semi-automatic identification interface using multi-layer OCR with top-k candidate selection.

## Files Modified

### 1. `frontend/src/services/api.js`

**Added OCR API methods:**

```javascript
export const ocrApi = {
    getCandidates: (copyId) => api.get(`/identification/copies/${copyId}/ocr-candidates/`),
    selectCandidate: (copyId, rank) => api.post(`/identification/copies/${copyId}/select-candidate/`, { rank }),
    performOCR: (copyId) => api.post(`/identification/perform-ocr/${copyId}/`)
};
```

**Purpose:** Provides clean API interface for OCR candidate operations.

### 2. `frontend/src/views/admin/IdentificationDesk.vue`

#### New State Variables

```javascript
const ocrCandidates = ref([])      // Top-5 student candidates
const ocrMode = ref('')             // AUTO, SEMI_AUTO, or MANUAL
const totalEngines = ref(0)         // Number of OCR engines consulted
const showManualSearchMode = ref(false)
```

#### New Functions

1. **`fetchOCRCandidates()`**
   - Automatically fetches OCR candidates when a copy is loaded
   - Handles 404 errors gracefully (no OCR result available)
   - Populates candidate list with confidence scores

2. **`selectOCRCandidate(candidate)`**
   - Provides visual feedback when candidate is clicked

3. **`confirmOCRCandidate(candidate)`**
   - Sends selected candidate rank to backend
   - Removes identified copy from queue
   - Loads next copy

4. **`showManualSearch()`**
   - Hides OCR candidates
   - Shows manual search interface
   - Focuses search input

#### UI Components

**OCR Candidate Cards:**
- Rank badge with gradient colors (gold for #1, silver for #2, bronze for #3)
- Student information (name, email, date of birth)
- Confidence bar with color coding:
  - Green (>70%): High confidence
  - Yellow (50-70%): Medium confidence
  - Orange (<50%): Low confidence
- Vote count indicator (number of engines in agreement)
- Expandable OCR source details
- "Select This Student" button per card

**Mode Indicator:**
- Header showing current OCR mode
- Number of engines consulted

**Manual Override:**
- "None of these? Manual Search" button
- Switches to traditional search interface

#### Conditional Rendering

- OCR candidates visible: Hides manual search, autocomplete, and validate button
- Manual search mode: Shows traditional interface
- Seamless fallback between modes

## Visual Design

### Candidate Card Styling

```css
/* High confidence (>60%) */
border-green-300 bg-green-50

/* Lower confidence */
border-gray-300 bg-white

/* Rank badge gradients */
Rank 1: from-yellow-400 to-yellow-600  /* Gold */
Rank 2: from-gray-300 to-gray-500      /* Silver */
Rank 3: from-orange-400 to-orange-600  /* Bronze */
Rank 4-5: from-blue-400 to-blue-600    /* Blue */
```

### Confidence Bar Colors

- Green gradient (>70%): `from-green-400 to-green-600`
- Yellow gradient (50-70%): `from-yellow-400 to-yellow-600`
- Orange gradient (<50%): `from-orange-400 to-orange-600`

## E2E Test Coverage

**File:** `frontend/tests/e2e/identification_ocr_flow.spec.ts`

### Test Scenarios

1. **Teacher can access identification desk**
   - Verifies authentication and routing

2. **Display OCR candidates with confidence scores**
   - Verifies candidate cards render correctly
   - Checks for 1-5 candidates
   - Validates presence of all required UI elements

3. **Expand OCR source details**
   - Tests expandable details functionality
   - Verifies OCR engine names displayed

4. **Select OCR candidate**
   - Tests candidate selection workflow
   - Mocks API response
   - Verifies navigation to next copy

5. **Fallback to manual search**
   - Tests manual override button
   - Verifies UI switches to manual mode
   - Confirms OCR candidates hidden

6. **Manual search and select student**
   - Tests traditional search interface
   - Mocks student search API
   - Verifies selection and validation

7. **Confidence score visual indicators**
   - Tests green/gray border styling
   - Verifies confidence bar presence

8. **Rank badges display correctly**
   - Tests rank numbers (1-5)
   - Verifies gold gradient for first place

## User Workflow

### Semi-Automatic Mode (OCR Confidence 40-70%)

1. Copy loads with header image displayed
2. OCR candidates automatically fetched and displayed
3. Teacher reviews top-5 candidates with confidence scores
4. Teacher can:
   - Click "Select This Student" on any candidate
   - Expand OCR details to see source engine outputs
   - Click "Manual Search" to override and search manually

### Automatic Mode (OCR Confidence >70%)

- Copy automatically identified
- Not shown in identification desk queue

### Manual Mode (OCR Confidence <40% or no OCR result)

- Traditional search interface displayed
- Teacher types student name/INE
- Autocomplete suggests matches
- Teacher selects and validates

## API Integration

### GET `/api/identification/copies/<copy_id>/ocr-candidates/`

**Response:**
```json
{
  "copy_id": "uuid",
  "anonymous_id": "COPY-001",
  "ocr_mode": "SEMI_AUTO",
  "total_engines": 3,
  "candidates": [
    {
      "rank": 1,
      "student": {
        "id": 1,
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean.dupont@example.com",
        "date_of_birth": "15/03/2008"
      },
      "confidence": 0.65,
      "vote_count": 2,
      "vote_agreement": 0.67,
      "ocr_sources": [
        {
          "engine": "tesseract",
          "variant": 0,
          "text": "DUPONT JEAN",
          "score": 0.7
        },
        {
          "engine": "easyocr",
          "variant": 1,
          "text": "DUPONT Jean",
          "score": 0.6
        }
      ]
    },
    // ... up to 5 candidates
  ]
}
```

### POST `/api/identification/copies/<copy_id>/select-candidate/`

**Request:**
```json
{
  "rank": 1
}
```

**Response:**
```json
{
  "success": true,
  "copy_id": "uuid",
  "student": {
    "id": 1,
    "first_name": "Jean",
    "last_name": "Dupont",
    "email": "jean.dupont@example.com"
  },
  "status": "READY"
}
```

## Browser Compatibility

- Modern browsers with ES6+ support
- Tailwind CSS utility classes
- SVG icons for visual feedback
- Responsive design (desktop-first for teacher workflow)

## Performance Considerations

1. **Lazy Loading:** OCR candidates fetched only when copy is displayed
2. **Error Handling:** Graceful 404 handling when no OCR result exists
3. **Async Operations:** All API calls are asynchronous with proper loading states
4. **Optimistic UI:** Candidate cards clickable immediately after render

## Future Enhancements

1. **Keyboard Navigation:** Arrow keys to navigate candidates, number keys to select
2. **Confidence Threshold Configuration:** Admin setting for auto/semi-auto thresholds
3. **OCR Engine Performance Metrics:** Dashboard showing which engines perform best
4. **Batch Operations:** Select multiple candidates at once for review
5. **Student Photo Preview:** Display student photo alongside candidate card
6. **Audit Trail Visualization:** Show identification history and corrections

## Validation Checklist

- [x] OCR candidate API methods created
- [x] IdentificationDesk.vue updated with candidate cards
- [x] Confidence visualization implemented
- [x] Rank badges styled correctly
- [x] Expandable OCR source details
- [x] Manual override functionality
- [x] E2E tests created (9 test scenarios)
- [x] Conditional rendering for mode switching
- [x] API integration with error handling
- [ ] Frontend unit tests (optional, Playwright E2E covers main flows)
- [ ] Accessibility testing (ARIA labels, keyboard navigation)
- [ ] Mobile responsive testing

## Known Limitations

1. **No Keyboard Shortcuts:** Currently mouse-only interaction (can add in future)
2. **No Undo:** Once candidate selected, cannot undo (matches existing behavior)
3. **No Student Photos:** Backend doesn't store photos yet
4. **Limited Mobile Support:** Designed primarily for desktop teacher workflow

## Deployment Notes

1. Ensure backend endpoints are deployed first
2. Frontend hot-reload will pick up changes automatically in dev mode
3. Production build: `npm run build`
4. E2E tests require backend running: `npx playwright test tests/e2e/identification_ocr_flow.spec.ts`

## Success Metrics

- **Identification Time Reduction:** Target 30-50% faster than pure manual search
- **User Satisfaction:** Teachers prefer semi-automatic mode (survey feedback)
- **Accuracy:** <5% correction rate on top-ranked candidates
- **Adoption:** >80% of identifications use OCR-assisted mode when available
