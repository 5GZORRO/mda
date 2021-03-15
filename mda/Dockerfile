FROM python:3.7

RUN pip install fastapi uvicorn uuid requests rsa pycryptodome typing kafka-python sqlalchemy sqlalchemy-utils psycopg2

EXPOSE 4000

COPY ./app /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000"]
