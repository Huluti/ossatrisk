
import asyncio

import httpx


class HttpClient:
    # connect fast, allow slow reads (packuments can be several MB)
    TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    MAX_CONCURRENCY = 10

    def __init__(self):
        self.client = httpx.Client(http2=True, timeout=self.TIMEOUT)
        self.async_client = httpx.AsyncClient(http2=True, timeout=self.TIMEOUT)
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)

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

    async def _request_async(self, method: str, url: str, **kwargs) -> httpx.Response | None:
        async with self._semaphore:
            try:
                response = await self.async_client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.RequestError:
                return None
            except httpx.HTTPStatusError:
                return None

    async def safe_get_async(self, url: str, **kwargs) -> httpx.Response | None:
        return await self._request_async("GET", url, **kwargs)

    async def safe_post_async(self, url: str, **kwargs) -> httpx.Response | None:
        return await self._request_async("POST", url, **kwargs)
