class HeadMethodMiddleware:
    """Map HEAD to GET so probes, curl -I, and strict proxies get 200 instead of 405."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "HEAD":
            await self.app(scope, receive, send)
            return

        scope = {**scope, "method": "GET"}
        started = False

        async def send_wrapper(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                await send(message)
            elif message["type"] == "http.response.body":
                if not started:
                    await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({**message, "body": b"", "more_body": False})

        await self.app(scope, receive, send_wrapper)
