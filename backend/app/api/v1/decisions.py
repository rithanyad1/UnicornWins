from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/decisions")
async def list_decisions(request: Request) -> dict:
    decisions = list(request.app.state.runtime.decisions.values())
    decisions.sort(key=lambda decision: decision["created_at"], reverse=True)
    return {"decisions": decisions}