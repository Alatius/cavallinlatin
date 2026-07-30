"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from . import config, db, security
from .routers import activity, admin, auth, comments, entries, locks, search


# 1 MB ceiling on any single request body — well above any legitimate XML
# entry but small enough that a hostile editor can't push gigabytes through
# the save endpoint.
MAX_BODY_BYTES = 1_000_000


class _BodyTooLarge(HTTPException):
    """Raised out of the wrapped receive() when the running total is exceeded.

    An HTTPException rather than a bare Exception on purpose: FastAPI wraps any
    other exception raised while parsing a request body into a generic
    400 "There was an error parsing the body", but re-raises HTTPException
    untouched ("If a middleware raises an HTTPException, it should be raised
    again"), so this surfaces as a proper 413.
    """

    def __init__(self) -> None:
        super().__init__(status_code=413, detail='Request body too large')


class BodySizeLimitMiddleware:
    """Reject request bodies larger than `max_bytes`, by counting bytes.

    Trusting Content-Length is not enough: a request sent with
    `Transfer-Encoding: chunked` carries no such header, and Starlette will
    buffer the whole stream before any handler sees it. Since /api/auth/login
    is unauthenticated and feeds its password field to Argon2, that turned one
    request into an out-of-memory lever against a `--workers 1` deployment.

    Pure ASGI rather than a BaseHTTPMiddleware hook so it can wrap `receive`
    and bail after the first oversized chunk instead of after the whole body.
    """

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # Declared oversize: refuse before reading a single byte.
        for name, value in scope.get('headers', ()):
            if name == b'content-length':
                try:
                    declared = int(value)
                except ValueError:
                    break
                if declared > self.max_bytes:
                    await self._reject(send)
                    return
                break

        total = 0
        started = False

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message['type'] == 'http.request':
                total += len(message.get('body', b''))
                if total > self.max_bytes:
                    raise _BodyTooLarge
            return message

        async def watched_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, watched_send)
        except _BodyTooLarge:
            # If the handler already began responding we can't replace it;
            # the connection just ends here.
            if not started:
                await self._reject(send)

    @staticmethod
    async def _reject(send) -> None:
        body = b'{"detail":"Request body too large"}'
        await send({
            'type': 'http.response.start',
            'status': 413,
            'headers': [
                (b'content-type', b'application/json'),
                (b'content-length', str(len(body)).encode()),
            ],
        })
        await send({'type': 'http.response.body', 'body': body})


def create_app() -> FastAPI:
    app = FastAPI(title='Cavallin Lexicon')
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_BODY_BYTES)

    with db.get_conn() as conn:
        # Sweep expired sessions on startup so the table doesn't grow
        # unbounded across years of runtime.
        conn.execute('DELETE FROM sessions WHERE expires_at < ?', (security.now(),))

    app.include_router(auth.router, prefix='/api/auth', tags=['auth'])
    app.include_router(entries.router, prefix='/api/entries', tags=['entries'])
    app.include_router(locks.router, prefix='/api/entries', tags=['locks'])
    app.include_router(comments.router, prefix='/api/entries', tags=['comments'])
    app.include_router(activity.router, prefix='/api/activity', tags=['activity'])
    app.include_router(search.router, prefix='/api', tags=['search'])
    app.include_router(admin.router, prefix='/api/admin', tags=['admin'])

    # Dev convenience: serve column images. In production, Apache serves
    # /cavallinlatin/columns/ directly from disk and this mount is unused.
    if config.COLUMNS_DIR.is_dir():
        app.mount(
            '/columns',
            StaticFiles(directory=str(config.COLUMNS_DIR)),
            name='columns',
        )
    return app


app = create_app()
