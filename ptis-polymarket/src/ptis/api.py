from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class PublicApiError(RuntimeError):
    """Raised when a public-data request cannot be completed safely."""


@dataclass(frozen=True)
class PublicApiClient:
    timeout_seconds: float = 20.0
    max_attempts: int = 3
    user_agent: str = "ptis-research/0.1"

    def get_json(self, base_url: str, path: str, params: dict[str, Any]) -> Any:
        query = urlencode(params, doseq=True)
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers={"User-Agent": self.user_agent})

        for attempt in range(1, self.max_attempts + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt == self.max_attempts:
                    raise PublicApiError(f"HTTP {exc.code} from {url}") from exc
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt == self.max_attempts:
                    raise PublicApiError(f"Unable to read valid JSON from {url}") from exc
            time.sleep(0.5 * (2 ** (attempt - 1)))

        raise AssertionError("retry loop exited unexpectedly")
