FROM python:3.13.0a6-slim-bullseye
RUN pip install requests python-dotenv loguru
COPY app .
CMD ["python", "-u", "./app.py"]