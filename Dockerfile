FROM nvcr.io/nvidia/pytorch:24.12-py3

WORKDIR /workspace

COPY requirements.txt .
RUN pip install -r requirements.txt --quiet

# Code wird als Volume gemountet (siehe compose.yml)
# -> Aenderungen am Code sofort sichtbar ohne rebuild
