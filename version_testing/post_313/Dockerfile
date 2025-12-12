FROM alpine:3.23

COPY --from=python:3.13.11-alpine3.23 /usr/local/ /usr/local/
COPY --from=python:3.14.2-alpine3.23 /usr/local/ /usr/local/

RUN apk add --no-cache bash git \
    && pip3.14 install --no-cache-dir tox==3.15.0
ENV TOX_PARALLEL_NO_SPINNER=1