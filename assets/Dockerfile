# Dockerfile for pysen-test
FROM alpine:3.14.6

COPY --from=python:3.6.13-alpine3.14 /usr/local/ /usr/local/
COPY --from=python:3.7.10-alpine3.14 /usr/local/ /usr/local/
COPY --from=python:3.8.13-alpine3.14 /usr/local/ /usr/local/
COPY --from=python:3.9.12-alpine3.14 /usr/local/ /usr/local/
COPY --from=python:3.10.4-alpine3.14 /usr/local/ /usr/local/

RUN apk add --no-cache expat gcc libffi musl-dev \
    && for MINOR in 6 7 8 9 10; do \
    sed "s|^#!/usr/local/bin/python$|#!/usr/local/bin/python3.${MINOR}|" \
    -i /usr/local/bin/*3.${MINOR}; done

RUN apk add --no-cache bash git \
    && pip3.10 install --no-cache-dir tox==3.15.0
ENV TOX_PARALLEL_NO_SPINNER 1
