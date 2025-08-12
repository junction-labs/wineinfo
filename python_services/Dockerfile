FROM python:3.12

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade uv
RUN uv pip install --system -r requirements.txt

# Pre-download the embedding model (this is the 70-second operation)
COPY ./bin ./bin
RUN python bin/pre_download_embeddings.py

COPY ./data ./data
COPY ./app .
