from fastapi import HTTPException


class BuildHTTPException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


def build_error_response(code: str, message: str) -> dict:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def build_success_response(data=None) -> dict:
    return {"success": True, "data": data, "error": None}
