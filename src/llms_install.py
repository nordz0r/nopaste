"""Install instance-aware /llms.txt before FastAPI routes register.

Imported from ``config`` (which ``main`` imports first) so the hardcoded
``llms_txt`` body in ``main`` is never registered as a route. The dead
string literal in ``main.llms_txt`` can be deleted in a follow-up that
rewrites ``src/main.py`` to call ``build_llms_txt`` directly.
"""
from __future__ import annotations

from typing import Any, Callable

_installed = False


def install() -> None:
    global _installed
    if _installed:
        return

    from fastapi.responses import PlainTextResponse
    from fastapi.routing import APIRouter

    _orig = APIRouter.add_api_route

    def add_api_route(
        self: APIRouter,
        path: str,
        endpoint: Callable[..., Any],
        **kwargs: Any,
    ):
        if path.rstrip("/") == "/llms.txt":
            endpoint = _llms_txt_endpoint
            kwargs["response_class"] = PlainTextResponse
            kwargs["include_in_schema"] = False
        return _orig(self, path, endpoint, **kwargs)

    APIRouter.add_api_route = add_api_route  # type: ignore[method-assign]
    _installed = True


async def _llms_txt_endpoint(request: Any):
    from fastapi.responses import PlainTextResponse

    import main as main_module
    from llms_txt import build_llms_txt

    return PlainTextResponse(
        build_llms_txt(
            request,
            resolve_public_base_url=main_module.resolve_public_base_url,
            shortener_host=main_module.shortener_host,
        )
    )


install()
