import secrets

from fastapi import Header, HTTPException, Request, status

from app.core.config import Settings


def validate_device_token(config: Settings, device_id: str, supplied: str | None) -> None:
    if device_id == "sentinel-esp32":
        configured, fallback = config.esp32_device_token, "dev-esp32-token"
    elif device_id == "sentinel-pico":
        configured, fallback = config.pico_device_token, "dev-pico-token"
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown device identity")
    expected = _configured_or_development_token(configured, fallback, config.app_env)
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials")


def _configured_or_development_token(configured: str, fallback: str, environment: str) -> str:
    if configured:
        return configured
    if environment.lower() == "development":
        return fallback
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is not configured")


def require_operator(request: Request, x_operator_key: str | None = Header(default=None)) -> None:
    config: Settings = request.app.state.runtime.config
    expected = _configured_or_development_token(
        config.operator_api_key, "dev-operator-token", config.app_env
    )
    if not x_operator_key or not secrets.compare_digest(x_operator_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid operator credentials")


def require_device(request: Request, device_id: str, x_device_token: str | None = Header(default=None)) -> None:
    validate_device_token(request.app.state.runtime.config, device_id, x_device_token)


def authenticated_device_id(request: Request, x_device_token: str | None) -> str:
    config: Settings = request.app.state.runtime.config
    for device_id in request.app.state.runtime.devices:
        try:
            validate_device_token(config, device_id, x_device_token)
        except HTTPException:
            continue
        return device_id
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials")