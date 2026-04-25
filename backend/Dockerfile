FROM python:3.11-slim
WORKDIR /app
# Build context MUST be the repo root (see render.yaml). If you ever set
# Render's "Root Directory" to `backend`, also change these COPYs back to
# bare `requirements.txt` / `.` — the two configs must stay in sync.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
