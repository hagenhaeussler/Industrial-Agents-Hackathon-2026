"""Domain failures shared by storage and HTTP/tool transports."""

class ServiceError(ValueError):
    def __init__(self, code: str, message: str, *, status: int = 400, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra

    def payload(self):
        return {"code": self.code, "message": self.message, **self.extra}
