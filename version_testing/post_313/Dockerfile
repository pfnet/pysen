FROM alpine:3.23

COPY --from=python:3.13.11-alpine3.23 /usr/local/ /usr/local/
COPY --from=python:3.14.2-alpine3.23 /usr/local/ /usr/local/

# sqlite-libs is required by mypy >=2, whose default cache backend uses sqlite3
# (mypy <2 used a filesystem metastore and did not need it).
RUN apk add --no-cache bash git sqlite-libs \
    && pip3.14 install --no-cache-dir tox==3.28.0
ENV TOX_PARALLEL_NO_SPINNER=1