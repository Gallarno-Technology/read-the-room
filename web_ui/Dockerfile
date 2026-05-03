FROM python:3.12-slim
WORKDIR /app
COPY web_ui/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x /app/web_ui/entrypoint.sh
ENTRYPOINT ["/app/web_ui/entrypoint.sh"]
CMD ["uvicorn", "web_ui.main:app", "--host", "0.0.0.0", "--port", "8888", "--no-access-log"]
