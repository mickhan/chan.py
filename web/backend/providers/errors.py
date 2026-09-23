class ProviderError(Exception):
    code = "SOURCE_ERROR"

    def __init__(self, message: str, supported_options: list[str] | None = None):
        super().__init__(message)
        self.message = message
        self.supported_options = supported_options


class UnsupportedPeriodError(ProviderError):
    code = "UNSUPPORTED_PERIOD"


class DateRangeUnavailableError(ProviderError):
    code = "DATE_RANGE_UNAVAILABLE"


class SourceDataError(ProviderError):
    code = "SOURCE_ERROR"


class SourceTimeoutError(ProviderError):
    code = "SOURCE_TIMEOUT"
