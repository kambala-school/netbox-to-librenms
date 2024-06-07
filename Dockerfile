FROM python:3.13.0b1-slim-bullseye
RUN pip install requests python-dotenv loguru
COPY app .
CMD ["python", "-u", "./app.py"]