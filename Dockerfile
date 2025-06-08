FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ARG USERNAME
ARG USER_ID
ARG GROUP_ID

RUN getent group ${GROUP_ID} || addgroup --gid ${GROUP_ID} ${USERNAME} \
    && adduser --disabled-password --gecos "" --uid ${USER_ID} --gid ${GROUP_ID} ${USERNAME}\
    && passwd -d ${USERNAME}

# Create and activate a virtual environment
RUN mkdir -p /opt/venv && \
    chown -R ${USER_ID}:${GROUP_ID} /opt/venv
USER ${USERNAME}
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install matplotlib==3.10.3 pandas==2.2.3 \
    streamlit==1.45.1 pydantic==2.11.5 numpy==1.26.4 stravalib==2.3 \
    https://github.com/ethanlee928/streamlit-oauth/releases/download/v0.1.14.1/streamlit_oauth-0.1.14-py3-none-any.whl

ENTRYPOINT [ "tail", "-f", "/dev/null" ]

FROM base AS prod

# Copy Strava API logo into streamlit oauth frontend dist
COPY --chown=${USERNAME}:${GROUP_ID} images/strava/btn_strava_connect_with_orange_x2.png /opt/venv/lib/python3.12/site-packages/streamlit_oauth/frontend/dist/
COPY --chown=${USERNAME}:${GROUP_ID} app /home/${USERNAME}/app

# Patch streamlit index.html to use Ferociter logo and title
COPY --chown=${USERNAME}:${GROUP_ID} app/logos/ferociter.ico /opt/venv/lib/python3.12/site-packages/streamlit/static/
RUN sed -i 's|<title>Streamlit</title>|<title>Ferociter</title>|' /opt/venv/lib/python3.12/site-packages/streamlit/static/index.html && \
    sed -i 's|<link rel="shortcut icon" href="./favicon.png" />|<link rel="shortcut icon" href="./ferociter.ico" />|' /opt/venv/lib/python3.12/site-packages/streamlit/static/index.html

WORKDIR /home/${USERNAME}/app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
