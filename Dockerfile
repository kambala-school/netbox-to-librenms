# syntax=docker/dockerfile:1

# Runtime DHI images have no shell/package manager, so install deps in a
# public builder and copy site-packages into the hardened runtime image.
FROM dhi.io/python:3-dev AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/packages -r requirements.txt

FROM dhi.io/python:3

ENV PYTHONPATH=/packages \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /packages /packages
COPY app .

CMD ["python", "-u", "./app.py"]
