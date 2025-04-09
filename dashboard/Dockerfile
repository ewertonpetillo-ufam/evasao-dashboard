FROM python:3.10-slim

WORKDIR /app

COPY requirements_dash.txt ./
RUN pip install --no-cache-dir -r requirements_dash.txt

COPY agentes/ ./agentes/
COPY dashboard/ ./

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]