"""Phase 7.7 - PDF + document builder package.

Houses the ReportLab-based PDF builder for doctor handouts and
KA family-handover documents. The builder calls the Phase 7.5
Rule #12 guard (`assert_min_primary_sources`) before any PDF
flush, so every PDF that ships from this package satisfies the
>= 5 primary-source constitutional rule by construction.

Public surface:
    PdfDocument, PdfSection - Pydantic typed inputs
    build_pdf, build_doctor_handout, build_family_handover_pdf
    PDFBuilderUnavailableError, PDFCitationError

Reference:
    v7_architecture/70_PHASES/77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md
    brain/common/pdf_guard.py (Rule #12 guard)
"""

from __future__ import annotations
