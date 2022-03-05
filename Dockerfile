FROM busybox:stable-musl as busybox

# --

FROM gcr.io/distroless/python3 AS base

ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COPY --from=busybox /bin/busybox /bin/busybox

RUN ["/bin/busybox", "--install", "-s", "/bin"]
RUN ln -s /bin/env /usr/bin/env

# --

FROM base AS build-env

# Install pip
ADD https://bootstrap.pypa.io/get-pip.py /src/get-pip.py
RUN python /src/get-pip.py

# Copy project files
RUN mkdir -p /src/tghook
COPY ./tghook /src/tghook/tghook
COPY ./poetry.lock ./pyproject.toml ./README.md /src/tghook/

WORKDIR /src/tghook

# Build project
RUN pip wheel --no-deps --use-pep517 .

# Install project in user local home
RUN find ./ -type f -name 'tghook-*.whl' -exec python -m pip install --upgrade --ignore-installed --user {}[cmd] \;

# Clear cache
RUN find /root/.local -type f -name '*.pyc' -delete
RUN find /root/.local -type d -name '__pycache__' | xargs -r rm -r

# Rename site-packages for copying to global path
RUN find /root/.local/lib -type d -name 'site-packages' | xargs -rn1 dirname | xargs -rI{} mv {}/site-packages {}/dist-packages
RUN find /root/.local -type f -exec chmod 644 {} +
RUN find /root/.local -type d -exec chmod 755 {} +
RUN chmod 755 -R /root/.local/bin

# --

FROM base

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
    org.opencontainers.image.revision="2" \
    org.opencontainers.image.licenses="GPL-2.0-or-later" \
    org.opencontainers.image.description="A simple library for creating telegram bots servers that exclusively use webhook for communication" \
    version.command="--version | awk -F' ' '{ print $2 }'"
