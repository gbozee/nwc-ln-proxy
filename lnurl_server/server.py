import os
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from service import handler, LN_ADDRESS_DOMAIN, LN_USERNAME
from urllib import parse


async def homepage(request):
    return JSONResponse({"message": "Welcome to the Node Remote API"})


def lnurlp(request: Request):
    encode = request.query_params.get("encode")
    amount = request.query_params.get("amount")
    description = request.query_params.get("description")
    username = LN_USERNAME
    user = handler.get_user(username)
    if amount:
        amount = int(amount)
    if description:
        handler.metadata_info = description
    result = handler.get_ln_details(username, amount)
    if result and user:
        if encode:
            params = {"amount": amount, "description": description}
            encoded_value = parse.urlencode(params)
            test_callback_url = (
                f"https://{LN_ADDRESS_DOMAIN}/lnurlp/{username}?{encoded_value}"
            )
            return JSONResponse(
                {"ln": handler.lnurl_address_encoded(test_callback_url)}
            )
        return JSONResponse(result.dict())
    return JSONResponse(
        {
            "status": "ERROR",
            "reason": "could not process request. please try again with valid parameters",
        },
        status_code=400,
    )


async def generate_invoice(request: Request):
    amount = request.query_params.get("amount")
    username = request.path_params.get("username")
    user = handler.get_user(username)
    if amount and user:
        result = handler.generate_invoice(
            username,
            int(amount),
        )
        if result:
            return JSONResponse(result.dict())
    return JSONResponse(
        {
            "reason": "could not process request. please try again with valid parameters",
            "status": "ERROR",
        },
        status_code=400,
    )


async def health_check(request):
    return JSONResponse({"status": "healthy"})


routes = [
    Route("/", endpoint=homepage),
    Route("/health", endpoint=health_check),
    Route(
        "/lnurlp/{username}/callback",
        endpoint=generate_invoice,
        methods=["GET"],
    ),
    Route("/lnurlp/{username}", lnurlp),
    Route("/.well-known/lnurlp/{username}", lnurlp, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
