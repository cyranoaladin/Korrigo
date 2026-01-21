---
name: canvas-interaction
description: Manages the drawing layer (red pen) on top of PDFs. Use for Phase 3 (Correction) tasks.
---

# Canvas Interaction Skill

## Architecture
The Canvas must be an **overlay** on top of `PDF.js` to allow annotations without modifying the underlying PDF during the correction phase.

## Data Structure
*   **Storage**: Annotations must be stored as **Vector Data (JSON)** (e.g., paths, points), NOT as rasterized images.
*   **Rasterization**: Rasterization only happens during the final export (Phase 4).

## Mathematics
Ensure **LaTeX formulas** can be rendered inside text annotation boxes, using libraries like KaTeX, as specified in the rules.
