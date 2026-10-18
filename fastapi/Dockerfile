FROM python:3.13-slim

WORKDIR /fastapi

COPY . .

RUN pip install -r requirements.txt
RUN playwright install --with-deps chromium

EXPOSE 8000

CMD fastapi run main.py