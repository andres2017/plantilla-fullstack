# Formato de error propio de este modulo ({code, message}), distinto del
# string plano que usa core/responses.py::error_response() en el resto del
# proyecto -- decision aprobada explicitamente para pagos (ver docs/DECISIONS.md),
# no una migracion del resto del proyecto.
from fastapi import HTTPException


class PaymentHTTPException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


def payment_error_response(code: str, message: str) -> dict:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def payment_success_response(data=None) -> dict:
    return {"success": True, "data": data, "error": None}
