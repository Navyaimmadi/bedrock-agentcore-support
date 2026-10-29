FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY app.py workflow.py gateway_client.py ./
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "app.py"]
