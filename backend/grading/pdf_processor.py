"""
PDF Processing Wrapper
Provides a clean interface for PDF operations, delegating to GradingService.
Separates concerns and facilitates test mocking.
"""


class PDFProcessor:
    """
    Wrapper for PDF import operations.
    Currently delegates to GradingService but provides a stable interface
    for tests and future refactoring.
    """

    @staticmethod
    def import_pdf(exam, pdf_file, user, anonymous_id=None):
        """
        Import a PDF and create a Copy with rasterization.

        Args:
            exam: Exam instance
            pdf_file: File object or file-like object
            user: User performing the import
            anonymous_id: Optional anonymous ID (generated if not provided)

        Returns:
            Copy instance (STAGING status)
        """
        from grading.services import GradingService

        # Currently, GradingService.import_pdf generates anonymous_id automatically
        # If we need to support custom anonymous_id, we'd modify GradingService
        # For now, we delegate and ignore the anonymous_id parameter
        # TODO: Extend GradingService.import_pdf to accept anonymous_id parameter
        return GradingService.import_pdf(exam, pdf_file, user)
