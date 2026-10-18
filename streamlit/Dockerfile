FROM python:3.13-slim

WORKDIR /streamlit

COPY . .

RUN pip install -r requirements.txt

CMD streamlit run streamlit_app.py --server.address=0.0.0.0