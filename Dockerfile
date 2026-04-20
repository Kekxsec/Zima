FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON=/usr/local/bin/python3.12 \
    UV_NO_MANAGED_PYTHON=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:${PATH}"

# Tool versions — bump these ARGs to upgrade; verify checksums still match after bumping.
ARG GRYPE_VERSION=0.84.0
ARG SYFT_VERSION=1.21.0
ARG TRIVY_VERSION=0.69.3
ARG OSQUERY_VERSION=5.12.1
# Pin mailcat to a specific commit (update the SHA when pulling upstream changes).
# To get the latest: git ls-remote https://github.com/sharsil/mailcat HEAD
ARG MAILCAT_COMMIT=849b32d1604a2809e296345f7ff82e0f1e09ff81

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lynis \
    && rm -rf /var/lib/apt/lists/*

# osquery — official Debian package with SHA256 verification
# To refresh the SHA: curl -fsSL https://pkg.osquery.io/deb/osquery_${OSQUERY_VERSION}-1.linux_amd64.deb | sha256sum
ARG OSQUERY_SHA256=051c287741d71b09184cb6bc53065cda972e3c27592b1e558696aaec9f0eb013
RUN set -eux; \
    curl -fsSL "https://pkg.osquery.io/deb/osquery_${OSQUERY_VERSION}-1.linux_amd64.deb" \
         -o /tmp/osquery.deb && \
    echo "${OSQUERY_SHA256}  /tmp/osquery.deb" | sha256sum -c - && \
    dpkg -i /tmp/osquery.deb && \
    rm /tmp/osquery.deb

# grype — vulnerability scanner
# Checksum file is fetched from the same release so no hardcoded SHA is needed.
RUN set -eux; \
    curl -fsSL "https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}/grype_${GRYPE_VERSION}_linux_amd64.tar.gz" \
         -o /tmp/grype_${GRYPE_VERSION}_linux_amd64.tar.gz && \
    curl -fsSL "https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}/grype_${GRYPE_VERSION}_checksums.txt" \
         -o /tmp/grype_checksums.txt && \
    cd /tmp && grep "grype_${GRYPE_VERSION}_linux_amd64.tar.gz" /tmp/grype_checksums.txt | sha256sum -c - && \
    tar -xzf /tmp/grype_${GRYPE_VERSION}_linux_amd64.tar.gz -C /usr/local/bin grype && \
    rm /tmp/grype_${GRYPE_VERSION}_linux_amd64.tar.gz /tmp/grype_checksums.txt

# syft — SBOM generator
RUN set -eux; \
    curl -fsSL "https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/syft_${SYFT_VERSION}_linux_amd64.tar.gz" \
         -o /tmp/syft_${SYFT_VERSION}_linux_amd64.tar.gz && \
    curl -fsSL "https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/syft_${SYFT_VERSION}_checksums.txt" \
         -o /tmp/syft_checksums.txt && \
    cd /tmp && grep "syft_${SYFT_VERSION}_linux_amd64.tar.gz" /tmp/syft_checksums.txt | sha256sum -c - && \
    tar -xzf /tmp/syft_${SYFT_VERSION}_linux_amd64.tar.gz -C /usr/local/bin syft && \
    rm /tmp/syft_${SYFT_VERSION}_linux_amd64.tar.gz /tmp/syft_checksums.txt

# trivy — vulnerability scanner
RUN set -eux; \
    curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" \
         -o /tmp/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz && \
    curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_checksums.txt" \
         -o /tmp/trivy_checksums.txt && \
    cd /tmp && grep "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" /tmp/trivy_checksums.txt | sha256sum -c - && \
    tar -xzf /tmp/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz -C /usr/local/bin trivy && \
    rm /tmp/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz /tmp/trivy_checksums.txt

RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --python /usr/local/bin/python3.12

# Extra Python-based OSINT tools — versions pinned in pyproject.toml
RUN uv run pip install --no-cache-dir \
    "socialscan==1.4.1" \
    "dnstwist==20240812" \
    "sherlock-project==0.15.0"

# mailcat — pinned to a specific commit, no install.sh
RUN set -eux; \
    curl -fsSL "https://github.com/sharsil/mailcat/archive/${MAILCAT_COMMIT}.tar.gz" \
         -o /tmp/mailcat.tar.gz && \
    mkdir -p /opt/mailcat && \
    tar -xzf /tmp/mailcat.tar.gz -C /opt/mailcat --strip-components=1 && \
    rm /tmp/mailcat.tar.gz; \
    if uv run pip install --no-cache-dir --retries 10 --default-timeout 120 \
        -r /opt/mailcat/requirements.txt; then \
        printf '#!/bin/sh\nexec /opt/venv/bin/python /opt/mailcat/mailcat.py "$@"\n' \
            > /usr/local/bin/mailcat && \
        chmod +x /usr/local/bin/mailcat; \
    else \
        echo "mailcat dependency install failed; continuing without mailcat binary" >&2; \
    fi

COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
