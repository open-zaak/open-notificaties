FROM python:3.12-alpine

WORKDIR /app
COPY server.py .

ENV PORT=8080
ENV HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "-u", "server.py"]
