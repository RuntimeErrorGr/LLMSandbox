FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HOME=/tmp/hf \
    ANONYMIZED_TELEMETRY=False \
    PYTHONPATH=/opt/sdk

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.15.0+cpu

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY sandbox_sdk.py network_lock_check.py /opt/sdk/

RUN useradd --uid 1000 --create-home runner
USER 1000
WORKDIR /tmp

CMD ["python", "/module/main.py"]
