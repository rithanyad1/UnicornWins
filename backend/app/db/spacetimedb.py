"""Minimal synchronous SpacetimeDB HTTP client.

The backend authenticates as a dedicated SpacetimeDB identity (``SPACETIMEDB_TOKEN``)
that the database owner registers through the module's ``SENTINEL_BACKEND_IDENTITY``
environment value. All tables are private, so:

* writes call module reducers: ``POST /v1/database/{db}/call/{reducer}``
* reads call the ``read_rows`` procedure, which returns a JSON-encoded string.

Calls are blocking; ``PersistenceService`` runs them in a worker thread. The token is
only ever sent in the Authorization header and is never included in errors or logs.
"""

import json
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SpacetimeDBError(RuntimeError):
    pass


class SpacetimeStore:
    def __init__(self, config: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.config = config
        self.available = False
        self.client: httpx.Client | None = None
        self.database = config.spacetimedb_database.strip()
        if self.database and config.spacetimedb_token.strip():
            self.client = httpx.Client(
                base_url=config.spacetimedb_uri.strip().rstrip("/"),
                headers={"Authorization": f"Bearer {config.spacetimedb_token.strip()}"},
                timeout=15.0,
                transport=transport,
            )
        else:
            logger.info("SpacetimeDB persistence is not configured")

    @property
    def configured(self) -> bool:
        return self.client is not None

    def _post(self, name: str, args: list[Any]) -> httpx.Response:
        if self.client is None:
            raise SpacetimeDBError("SpacetimeDB is not configured")
        try:
            response = self.client.post(f"/v1/database/{self.database}/call/{name}", json=args)
        except httpx.HTTPError as exc:
            raise SpacetimeDBError(f"{name}: {type(exc).__name__}: {exc}") from None
        if response.status_code >= 400:
            raise SpacetimeDBError(
                f"{name} failed ({response.status_code}): {response.text[:300]}"
            )
        self.available = True
        return response

    def call_reducer(self, reducer: str, args: list[Any]) -> None:
        self._post(reducer, args)

    def call_procedure(self, procedure: str, args: list[Any]) -> Any:
        """Call a procedure and return its decoded result.

        String-returning procedures come back as a JSON string; that string is
        itself JSON (for ``read_rows``), so it is decoded a second time.
        """
        result = self._post(procedure, args).json()
        if isinstance(result, str):
            return json.loads(result)
        return result

    def read_rows(self, table: str, since_micros: int, limit: int) -> list[dict[str, Any]]:
        rows = self.call_procedure("read_rows", [table, since_micros, limit])
        if not isinstance(rows, list):
            raise SpacetimeDBError(f"read_rows returned unexpected data for {table}")
        return rows

    def ping(self) -> bool:
        if self.client is None:
            self.available = False
            return False
        try:
            self.read_rows("facilities", 0, 1)
        except SpacetimeDBError:
            self.available = False
            raise
        return True

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
