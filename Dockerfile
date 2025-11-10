# --- Base image ---
FROM python:3.10-slim

# --- Set workdir ---
WORKDIR /app

# --- Copy source code ---
COPY . /app

# --- Install dependencies ---
RUN pip install --no-cache-dir -r requirements.txt

# --- Set Flask environment variables ---
ENV FLASK_APP=manage.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production

# --- Expose port ---
EXPOSE 5000

# --- Run the app ---
CMD ["flask", "run"]
