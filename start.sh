#!/bin/bash

. .venv/bin/activate


export OTEL_RESOURCE_ATTRIBUTES=service.name=AudioManipulator
export OTEL_EXPORTER_OTLP_ENDPOINT=http://174.138.34.94:4317 
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc   

opentelemetry-instrument gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app --timeout 300