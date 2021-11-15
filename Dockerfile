FROM busybox:stable-musl as busybox

# --

FROM gcr.io/distroless/python3 AS base

ENV PATH            /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV XDG_DATA_HOME   /data
ENV XDG_CONFIG_HOME /config

COPY --from=busybox /bin/busybox /bin/busybox

RUN ["/bin/busybox", "--install", "-s", "/usr/bin"]

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

# --

FROM base

COPY --from=build-env /root/.local/ /usr/local/

ENV LOG_PATH=/var/log/tghook

VOLUME /var/log/tghook

EXPOSE 8443

CMD ["/usr/local/bin/tghook"]
