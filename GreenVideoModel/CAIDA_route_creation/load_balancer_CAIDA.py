import httpx
import itertools
from fastapi import FastAPI, Request, Response
# from fastapi.responses import StreamingResponse

# --- Configuration ---
BACKENDS = [
    "http://obelix125:5000",
    "http://obelix126:5000",
    "http://obelix127:5000"
]

# --- Round-robin iterator ---
_pool = itertools.cycle(BACKENDS)

app = FastAPI()


def next_backend() -> str:
    return next(_pool)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy(request: Request, path: str):
    target = next_backend()
    url = f"{target}/{path}"
    # print("HELLO!")
    # print(url)
    if request.url.query:
        url += f"?{request.url.query}"

    body = await request.body()
    try:
        async with httpx.AsyncClient() as client:
            proxied = await client.request(
                method=request.method,
                url=url,
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                content=body,
                follow_redirects=True,
                # timeout=240.0
                timeout=None
            )
    except httpx.ReadTimeout as rte:
        print(url, flush=True)
        return Response(
            content=None,
            status_code=400,
            headers={},
        )


    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=dict(proxied.headers),
    )
