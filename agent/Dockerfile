FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY spectis_agent/ ./spectis_agent/

ENTRYPOINT ["spectis-agent"]
CMD ["scan"]
