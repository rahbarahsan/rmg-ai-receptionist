import json
import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.auth import verify_tool_secret
from app.tools.registry import is_tool_name, run_tool

logger = logging.getLogger("reorder.tools")
router = APIRouter()


@router.post("/api/agent/tools/{tool}")
async def call_tool(tool: str, request: Request) -> JSONResponse:
    """One POST per tool. Shared-secret auth, JSON body validated by the tool's schema.

    Contract (ported from the TS route): 401 unauthorized, 404 unknown tool, 400
    unparseable JSON, else 200 even for `{ok: false}` results. Every response carries
    an `x-tool-ms` latency header; warn if a handler blows the 500ms budget.
    """
    if not verify_tool_secret(request.headers.get("x-agent-secret")):
        return JSONResponse({"ok": False, "reason": "unauthorized"}, status_code=401)
    if not is_tool_name(tool):
        return JSONResponse({"ok": False, "reason": "unknown tool"}, status_code=404)

    raw = await request.body()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "reason": "invalid input"}, status_code=400)

    start = time.perf_counter()
    result = await run_in_threadpool(run_tool, tool, payload)
    ms = int((time.perf_counter() - start) * 1000)
    if ms > 500:
        logger.warning("tool %s took %dms (>500ms budget)", tool, ms)
    return JSONResponse(result, headers={"x-tool-ms": str(ms)})
