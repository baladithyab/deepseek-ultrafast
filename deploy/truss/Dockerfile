# Truss base image: the serve image plus what a Baseten custom server build needs.
# docker build -f deploy/Dockerfile -t deepseek-ultrafast . && docker build -f deploy/truss/Dockerfile -t <registry>/deepseek-ultrafast:truss deploy/truss
ARG BASE=deepseek-ultrafast
FROM ${BASE}
# Truss requires Python on PATH; Redis runs beside serve in the same container.
RUN apt-get update && apt-get install -y --no-install-recommends python3 redis-server && rm -rf /var/lib/apt/lists/*
ENTRYPOINT []
