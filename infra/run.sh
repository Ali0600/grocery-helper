#!/bin/sh
# The Lambda handler. The web adapter (a layer, registered as an extension) starts this,
# waits for AWS_LWA_READINESS_CHECK_PATH to answer, and from then on translates each Lambda
# invocation into a plain HTTP request against this local uvicorn.
#
# `python -m uvicorn` rather than the `uvicorn` console script: the package root (/var/task)
# is on sys.path for `python -m` but the console script's shebang points into a directory
# that does not exist here, and dependencies are installed at the root of the zip rather
# than into a site-packages tree.
#
# Bound to 127.0.0.1 deliberately — nothing outside the execution environment should be able
# to reach this process; the adapter is the only client.
exec python -m uvicorn app.main:app --host 127.0.0.1 --port "${AWS_LWA_PORT:-8080}"
