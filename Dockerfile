FROM busybox:stable-musl as busybox

FROM gcr.io/distroless/python3 AS base

ENV PATH            /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV XDG_DATA_HOME   /data
ENV XDG_CONFIG_HOME /config

COPY --from=busybox /bin/busybox    /bin/busybox

RUN ["/bin/busybox", "--install", "-s", "/usr/bin"]

FROM base AS build-env

WORKDIR /src/tghook

COPY tghook poetry.lock poetry.toml pyproject.toml ./

# Install poetry
RUN wget -q -O - -o /dev/null 'https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py' \
    | env POETRY_HOME=/usr/local python -

# Install package in local venv
RUN env PYTHONDONTWRITEBYTECODE=1 POETRY_VIRTUALENVS_IN_PROJECT=true \
    poetry install --no-dev -E cmd
# Remove build dependencies
RUN env PYTHONDONTWRITEBYTECODE=1 POETRY_VIRTUALENVS_IN_PROJECT=true \
    poetry run pip uninstall -y pip wheel
# Remove symlinks
RUN find .venv/ -type l -delete
# Remove cache files
RUN find .venv/ -type d -name '__pycache__' | xargs -r rm -r
RUN find .venv/ -type f -name '*.pyc' -delete
# Remove venv specific executables
RUN rm .venv/bin/{activate*,deactivate*}
# Remove from .venv files already present in system
RUN set -eux; \
    # Remove common binaries between system and venv
    && find "$(dirname "$(realpath "$(command -v python)")")" -mindepth 1 -maxdepth 1 -exec basename {} \; | sort >/tmp/system_bin \
    && cd .venv/bin \
    && find .venv/bin -mindepth 1 -maxdepth 1 -exec basename {} \; \
        | sort >/tmp/venv_bin \
        | comm -12 - /tmp/system_bin \
        | xargs -r rm -r \


# FROM base

# COPY --from=build-env /app /app


# CMD ["hello.py", "/etc"]
