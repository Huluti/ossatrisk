
import httpx


class HttpClient:
    # connect fast, allow slow reads (packuments can be several MB)
    TIMEOUT = httpx.Timeout(30.0, connect=10.0)

    def __init__(self):
        self.client = httpx.Client(http2=True, timeout=self.TIMEOUT)

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
