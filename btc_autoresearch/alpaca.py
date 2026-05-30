from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_PAPER_BASE_URL = "https://paper-api.alpaca.markets"


@dataclass(frozen=True)
class AlpacaCredentials:
    base_url: str
    key_id: str
    secret_key: str


def load_alpaca_credentials(config: dict) -> AlpacaCredentials | None:
    paper_config = config.get("paper_trading", {})
    base_url = os.environ.get("APCA_API_BASE_URL") or paper_config.get("alpaca_base_url") or DEFAULT_PAPER_BASE_URL
    key_id = os.environ.get("APCA_API_KEY_ID")
    secret_key = os.environ.get("APCA_API_SECRET_KEY")
    if not key_id or not secret_key:
        return None
    return AlpacaCredentials(base_url=base_url.rstrip("/"), key_id=key_id, secret_key=secret_key)


REQUEST_ID_HEADER = "X-Request-ID"


class AlpacaPaperClient:
    def __init__(self, credentials: AlpacaCredentials) -> None:
        self.credentials = credentials
        # Alpaca recommends persisting recent Request IDs for support; the most recent ones are kept here.
        self.last_request_id: str | None = None
        self.request_ids: list[str] = []

    def get_account(self) -> dict[str, Any]:
        return self._request("GET", "/v2/account")

    def submit_crypto_market_order(self, symbol: str, qty: float, side: str = "buy") -> dict[str, Any]:
        payload = {
            "symbol": symbol,
            "qty": f"{qty:.8f}",
            "side": side,
            "type": "market",
            "time_in_force": "gtc",
        }
        return self._request("POST", "/v2/orders", payload)

    def _record_request_id(self, request_id: str | None) -> str | None:
        if request_id:
            self.last_request_id = request_id
            self.request_ids.append(request_id)
            print(f"[alpaca] {REQUEST_ID_HEADER}: {request_id}")
        return request_id

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.credentials.base_url}{path}",
            data=body,
            method=method,
            headers={
                "APCA-API-KEY-ID": self.credentials.key_id,
                "APCA-API-SECRET-KEY": self.credentials.secret_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                self._record_request_id(response.headers.get(REQUEST_ID_HEADER))
                result = json.loads(response.read().decode("utf-8"))
                if isinstance(result, dict):
                    result["_request_id"] = self.last_request_id
                return result
        except HTTPError as exc:
            # Persist the Request ID even on failure — it is what Alpaca support needs to trace the call.
            request_id = self._record_request_id(exc.headers.get(REQUEST_ID_HEADER) if exc.headers else None)
            detail = exc.read().decode("utf-8")
            raise RuntimeError(
                f"Alpaca API error {exc.code} (request_id={request_id}): {detail}"
            ) from exc
