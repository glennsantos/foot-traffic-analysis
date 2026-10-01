"""Analysis failures usable without importing the geospatial stack."""


class AnalysisTimeoutError(Exception):
    pass


class AnalysisUpstreamError(Exception):
    pass
