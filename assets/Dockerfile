# Dockerfile for pysen-test
FROM alpine:3.17

COPY --from=python:3.7.16-alpine3.17 /usr/local/ /usr/local/
COPY --from=python:3.8.16-alpine3.17 /usr/local/ /usr/local/
COPY --from=python:3.9.16-alpine3.17 /usr/local/ /usr/local/
COPY --from=python:3.10.11-alpine3.17 /usr/local/ /usr/local/
COPY --from=python:3.11.3-alpine3.17 /usr/local/ /usr/local/

RUN apk add --no-cache expat gcc libffi musl-dev \
    && for MINOR in 7 8 9 10 11; do \
    sed "s|^#!/usr/local/bin/python$|#!/usr/local/bin/python3.${MINOR}|" \
    -i /usr/local/bin/*3.${MINOR}; done

RUN apk add --no-cache bash git \
    && pip3.11 install --no-cache-dir tox==3.15.0
ENV TOX_PARALLEL_NO_SPINNER 1
