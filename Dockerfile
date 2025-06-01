FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS base

# Create and activate a virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install matplotlib pandas \
    streamlit pydantic numpy==1.26.4 stravalib \
    https://github.com/ethanlee928/streamlit-oauth/releases/download/v0.1.14.1/streamlit_oauth-0.1.14-py3-none-any.whl

ENTRYPOINT [ "tail", "-f", "/dev/null" ]

FROM base AS prod

COPY app .

# Copy Strava API logo into streamlit oauth frontend dist
COPY images/strava/btn_strava_connect_with_orange_x2.png /opt/venv/lib/python3.13/site-packages/streamlit_oauth/frontend/dist/
EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
