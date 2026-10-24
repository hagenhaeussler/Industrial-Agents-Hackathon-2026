"""Domain errors with the codes shared by server and UI (CONTRACTS §14)."""

from starter_agent.building_map import MapError


class CoreError(MapError):
    def __init__(self, code: str, message: str, candidates=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.candidates = candidates or []

    def as_dict(self):
        return {"code": self.code, "message": self.message, "candidates": self.candidates}


class EditError(CoreError):
    pass
