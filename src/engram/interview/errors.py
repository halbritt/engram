from __future__ import annotations


class InterviewError(RuntimeError):
    """Domain root for ``engram.interview`` errors (RFC 0021)."""


class GoldLabelStorageError(InterviewError):
    """Raised when an append-only or parent-validation guard rejects a write."""


class GoldLabelSamplerError(InterviewError):
    """Raised when the stratified sampler cannot honor its contract."""


class GoldLabelVerdictError(InterviewError):
    """Raised when the agent receives a verdict outside ``VALID_VERDICTS``."""
