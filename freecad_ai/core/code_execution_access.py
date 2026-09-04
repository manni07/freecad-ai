"""Process-only authorization for AI-proposed Python execution."""


class CodeExecutionAccess:
    """In-memory capability gate; never reads or writes configuration."""

    def __init__(self):
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def arm(self) -> None:
        self._active = True

    def disarm(self) -> None:
        self._active = False


_code_execution_access: "CodeExecutionAccess | None" = None


def get_code_execution_access() -> CodeExecutionAccess:
    """Return the process-wide code-execution capability gate."""
    global _code_execution_access
    if _code_execution_access is None:
        _code_execution_access = CodeExecutionAccess()
    return _code_execution_access
