# TODO: Fix Port Binding and MongoDB Connection Warnings

## Issues Identified
1. **Port Binding Warning**: Render's health check uses HEAD request on the root endpoint (/), but the endpoint only handles GET, returning 405 Method Not Allowed. This causes "No open ports detected" during scanning.
2. **MongoDB Connection**: SSL handshake failure due to TLS version incompatibility. MongoDB Atlas requires TLS 1.2+, but the client may be using an older version.

## Fixes Implemented
- [x] Update root endpoint in `main.py` to handle both GET and HEAD methods.
- [x] Update MongoDB connection in `database_mongo.py` to enforce TLS 1.2.

## Summary of Changes
- Modified the root endpoint in `main.py` to use `@app.api_route("/", methods=["GET", "HEAD"])` instead of `@app.get("/")` to allow HEAD requests for Render's health checks.
- Added `ssl_context=ssl.create_default_context()` to the AsyncIOMotorClient in `database_mongo.py` to enforce TLS 1.2 for MongoDB connections.

## Followup Steps
- [ ] Test the changes by redeploying to Render.
- [ ] Verify that the warnings are resolved in the logs.
- [ ] Ensure the application starts without errors.
