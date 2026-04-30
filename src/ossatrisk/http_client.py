import httpx
from typing import Optional


class HttpClient:
    def __init__(self):
        self.client = httpx.Client(http2=True)

    def safe_get(self, url: str, **kwargs) -> Optional[httpx.Response]:
        try:
            response = self.client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.RequestError:
            return None
        except httpx.HTTPStatusError:
            return None
