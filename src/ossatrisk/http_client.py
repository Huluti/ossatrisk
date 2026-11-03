import asyncio

import httpx


class HttpClient:
    # connect fast, allow slow reads (packuments can be several MB)
    TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    MAX_CONCURRENCY = 10
    RETRY_ATTEMPTS = 4

    def __init__(self):
        self.client = httpx.AsyncClient(http2=True, timeout=self.TIMEOUT)
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)

    async def _request_once(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response | None:
        async with self.semaphore:
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.RequestError:
                return None
            except httpx.HTTPStatusError:
                return None

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response | None:
        # registries rate-limit; back off and retry before giving up
        for i in range(self.RETRY_ATTEMPTS):
            response = await self._request_once(method, url, **kwargs)
            if response is not None:
                return response
            if i < self.RETRY_ATTEMPTS - 1:
                await asyncio.sleep(1 + i)
        return None

    async def safe_get(self, url: str, **kwargs) -> httpx.Response | None:
        return await self._request("GET", url, **kwargs)

    async def safe_post(self, url: str, **kwargs) -> httpx.Response | None:
        return await self._request("POST", url, **kwargs)
