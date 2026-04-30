"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, security
from .routers import activity, admin, auth, comments, entries, locks, search


# 1 MB ceiling on any single request body — well above any legitimate XML
# entry but small enough that a hostile editor can't push gigabytes through
# the save endpoint.
MAX_BODY_BYTES = 1_000_000


def create_app() -> FastAPI:
    app = FastAPI(title='Cavallin Lexicon')

    with db.get_conn() as conn:
        # Sweep expired sessions on startup so the table doesn't grow
        # unbounded across years of runtime.
        conn.execute('DELETE FROM sessions WHERE expires_at < ?', (security.now(),))

    @app.middleware('http')
    async def limit_body_size(request: Request, call_next):
        cl = request.headers.get('content-length')
        if cl is not None:
            try:
                if int(cl) > MAX_BODY_BYTES:
                    return JSONResponse(
                        {'detail': 'Request body too large'},
                        status_code=413,
                    )
            except ValueError:
                pass
        return await call_next(request)

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
