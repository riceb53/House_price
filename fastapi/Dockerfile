FROM python:3.13-slim

WORKDIR /fastapi

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD fastapi run permits_api.py