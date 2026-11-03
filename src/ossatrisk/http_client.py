
import httpx


class HttpClient:
    def __init__(self):
        self.client = httpx.Client(http2=True)

    def safe_get(self, url: str, **kwargs) -> httpx.Response | None:
        try:
            response = self.client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.RequestError:
            return None
        except httpx.HTTPStatusError:
            return None

    def safe_post(self, url: str, **kwargs) -> httpx.Response | None:
        try:
            response = self.client.post(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.RequestError:
            return None
        except httpx.HTTPStatusError:
            return None
