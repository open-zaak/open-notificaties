from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, Response
import asyncio
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Webhook simulator running"}

@app.api_route("/204", methods=["POST"])
async def webhook(request: Request, delay: int = Query(0, ge=0)):
    """
    Simulate webhook responses with optional delay or 204 response.
    :param delay: artificial delay in seconds to simulate timeout
    :param no_content: if True, return HTTP 204 No Content
    """
    if delay > 0:
        await asyncio.sleep(delay)

    return Response(status_code=204)

@app.api_route("/400", methods=["POST"])
async def webhook_error(message: str = Query("Bad Request")):
    """
    Always returns 400 Bad Request
    :param message: optional error message in JSON body
    """
    return JSONResponse(status_code=400, content={"error": message})
