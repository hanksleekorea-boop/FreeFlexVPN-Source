FROM python:3.13.7-slim@sha256:eed456c4f4bd5a1d5d47f8e9cce7a1199f187d76d93904092adbc88d615d2e86

RUN apt-get update \
 && apt-get install -y --no-install-recommends git gh ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 collaboration
WORKDIR /srv/freeflexvpn
COPY 20_SRC/app/ /srv/freeflexvpn/20_SRC/app/
COPY 20_SRC/html_templates/collaboration_portal.html 20_SRC/html_templates/collaboration-portal.js /srv/freeflexvpn/20_SRC/html_templates/
ENV PYTHONPATH=/srv/freeflexvpn/20_SRC \
    FFVPN_COLLAB_HOST=0.0.0.0 \
    FFVPN_COLLAB_PORT=8790
USER collaboration
EXPOSE 8790
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8790/healthz', timeout=2)"
CMD ["python", "-m", "app.collaboration_http"]
