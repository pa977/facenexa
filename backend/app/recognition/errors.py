"""
Custom exception hierarchy for the FaceNexa recognition subsystem.

Separates AI errors from general application errors so the backend
can remain stable when models fail or frames are invalid.
"""


class RecognitionError(Exception):
    """Base exception for all recognition-subsystem errors."""

    def __init__(self, message: str = "Recognition error", detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class ModelLoadError(RecognitionError):
    """Raised when an AI model fails to load (missing file, corrupt ONNX, etc.)."""

    def __init__(self, model_name: str, detail: str | None = None):
        self.model_name = model_name
        super().__init__(
            message=f"Failed to load model: {model_name}",
            detail=detail,
        )


class DetectionError(RecognitionError):
    """Raised when face detection fails on a frame."""

    def __init__(self, detail: str | None = None):
        super().__init__(message="Face detection failed", detail=detail)


class EmbeddingError(RecognitionError):
    """Raised when embedding generation fails."""

    def __init__(self, detail: str | None = None):
        super().__init__(message="Embedding generation failed", detail=detail)


class QualityError(RecognitionError):
    """Raised when face quality analysis fails."""

    def __init__(self, detail: str | None = None):
        super().__init__(message="Face quality analysis failed", detail=detail)


class AlignmentError(RecognitionError):
    """Raised when face alignment fails."""

    def __init__(self, detail: str | None = None):
        super().__init__(message="Face alignment failed", detail=detail)
