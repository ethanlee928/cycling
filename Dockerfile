FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS base

# Create and activate a virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install matplotlib pandas \
    streamlit streamlit-oauth pydantic numpy==1.26.4

ENTRYPOINT [ "tail", "-f", "/dev/null" ]

FROM base AS prod

COPY app .
EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
