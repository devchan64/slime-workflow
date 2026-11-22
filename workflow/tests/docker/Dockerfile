FROM node:22-bookworm-slim AS node
FROM python:3.14-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && apt-get update && apt-get install -y --no-install-recommends git bubblewrap ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/deps
COPY requirements.txt .
COPY workflow/requirements.txt workflow/requirements.txt
RUN python -m venv /opt/runtime && /opt/runtime/bin/pip install --no-cache-dir -r workflow/requirements.txt httpx
RUN /opt/runtime/bin/pip install --no-cache-dir torch==2.13.0+cpu --index-url https://download.pytorch.org/whl/cpu && /opt/runtime/bin/pip install --no-cache-dir scipy==1.18.0
RUN /opt/runtime/bin/pip install --no-cache-dir 'diffusers @ git+https://github.com/huggingface/diffusers.git@8c54b38fea3d624d23d0e43c0c96037f080a79f9' transformers==5.23.0 accelerate==1.15.0 safetensors==0.8.0
COPY generators/hermes_agent/requirements-mcp.lock .
RUN python -m venv /opt/hermes-mcp && /opt/hermes-mcp/bin/pip install --no-cache-dir -r requirements-mcp.lock
COPY gui/package*.json gui/
RUN cd gui && npm ci
ENV PATH="/opt/runtime/bin:${PATH}" HOME=/tmp
WORKDIR /workspace/slime-workflow
