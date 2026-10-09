class ValidationError(ValueError):
    """Raised when an input violates a business rule.

    ``code`` is a stable machine-readable identifier that test cases assert on,
    so a test checks *which* rule fired, not just that something failed.
    """

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class StateError(ValueError):
    """Raised on an illegal booking state transition."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
