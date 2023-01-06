FROM python:3.10-slim
ADD ./autoupdate /app/autoupdate
ADD ./*.py /app/
COPY requirements.txt app/requirements.txt
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt --target=/app
