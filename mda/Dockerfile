FROM python:3.10.0-alpine3.15

ENV TZ="Europe/Lisbon"

RUN pip install fastapi uvicorn uuid requests rsa pycryptodome typing kafka-python sqlalchemy==1.3.23 sqlalchemy-utils psycopg2 python-dateutil timeloop

VOLUME /logs

EXPOSE 4000

COPY ./app /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0",  "--port", "4000"]
