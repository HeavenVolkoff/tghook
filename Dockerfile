FROM python:3.10-alpine AS build-env

# Copy project files
RUN mkdir -p /srv/tghook
COPY ./tghook /srv/tghook/tghook
COPY ./poetry.lock ./pyproject.toml ./README.md /srv/tghook/

WORKDIR /srv/tghook

RUN apk add rust cargo patchelf build-base libffi-dev openssl-dev
RUN pip install -U pip setuptools wheel

# Build project
RUN pip wheel --no-deps --use-pep517 .

# Install project in user local home
RUN find ./ -type f -name 'tghook-*.whl' -exec python -m pip install --upgrade --ignore-installed --user {}[cmd] \;

# Clear cache
RUN find /root/.local -type f -name '*.pyc' -delete
RUN find /root/.local -type d -name '__pycache__' | xargs -r rm -r

# Fix permissions
RUN find /root/.local -type f -exec chmod 644 {} +
RUN find /root/.local -type d -exec chmod 755 {} +
RUN chmod 755 -R /root/.local/bin

# --

FROM python:3.10-alpine

ENV TZ=UTC \
    PUID=1000 \
    PGID=1000 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TMPDIR=/tmp \
    LANGUAGE=en \
    LOG_PATH=/var/log/tghook

COPY --from=build-env /root/.local/ /usr/local/
COPY --chmod=755 entrypoint.sh /bin/

VOLUME /var/log/tghook

EXPOSE 8443

ENTRYPOINT [ "/bin/entrypoint.sh" ]

LABEL org.opencontainers.image.title="tghook" \
    org.opencontainers.image.authors="Vítor Vasconcellos <support@vasconcellos.casa>" \
    org.opencontainers.image.revision="1" \
    org.opencontainers.image.licenses="GPL-2.0-or-later" \
    org.opencontainers.image.description="A simple library for creating telegram bots servers that exclusively use webhook for communication" \
    version.command="--version | tail -n1 | awk '{ print \$2 }'"
