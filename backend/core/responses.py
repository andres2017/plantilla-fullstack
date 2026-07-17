from math import ceil


def success_response(data=None):
    return {"success": True, "data": data, "error": None}


def error_response(error: str):
    return {"success": False, "data": None, "error": error}


def paginated_response(items: list, total: int, page: int, limit: int):
    return success_response({
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": ceil(total / limit) if limit else 0,
        },
    })
