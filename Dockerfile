# syntax=docker/dockerfile:1
FROM python:3.13.0b2-slim-bullseye
RUN pip install requests python-dotenv loguru
COPY app .
CMD ["python", "-u", "./app.py"]