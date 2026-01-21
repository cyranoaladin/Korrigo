---
name: pdf-processing
description: Handles PDF slicing, OpenCV detection, and merging. Use for Phase 1 (Ingestion) tasks.
---

# PDF Processing Skill

## Context
Refer to the "Booklet/Stapler" logic in `@SPEC.md`. This skill involves detecting headers to identify booklets and managing the merging of pages into copies.

## Tools
*   **Detection**: Use `opencv-python` for header detection on page images.
*   **Manipulation**: Use `pypdf` or `pdf2image` for slicing, merging, and converting PDFs.

## Warning
**Always ensure coordinate systems for cropping/masking are resolution-independent.** PDF points and Image pixels may differ.
