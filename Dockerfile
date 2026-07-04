# syntax=docker/dockerfile:1
<<<<<<< HEAD

# Runtime DHI images have no shell/package manager, so install deps in a
# public builder and copy site-packages into the hardened runtime image.
FROM python:3.14-slim-bookworm AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/packages -r requirements.txt

FROM dhi.io/python:3.14

ENV PYTHONPATH=/packages \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /packages /packages
=======
FROM python:3.14.0rc1-slim-bullseye
RUN pip install requests python-dotenv loguru
>>>>>>> 2a695c7e622c0326837d6491e9a2178b9eb3b73f
COPY app .

CMD ["python", "-u", "./app.py"]
