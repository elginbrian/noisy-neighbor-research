FROM python:3.12-slim

# Variabel lingkungan standar dan nilai default parameter beban
ENV PYTHONUNBUFFERED=1 \
    CPU_ITERATIONS=100 \
    MEM_MB_PER_REQ=4 \
    MEM_TARGET_MB=640

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

# Menjalankan 1 worker tanpa access-log agar tidak menimbulkan disk I/O buatan
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--log-level", "warning"]
