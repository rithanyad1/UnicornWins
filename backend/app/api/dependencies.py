from fastapi import Request

from app.services.runtime import Runtime


def get_app_runtime(request: Request) -> Runtime:
    return request.app.state.runtime