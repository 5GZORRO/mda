FROM alpine:3

ENV TZ="Europe/Lisbon"

RUN apk add py3-pip build-base postgresql-libs musl-dev postgresql-dev python3-dev

RUN pip install fastapi uvicorn uuid requests rsa pycryptodome typing kafka-python sqlalchemy==1.3.23 sqlalchemy-utils psycopg2 python-dateutil timeloop

VOLUME /logs

EXPOSE 4000

COPY ./app /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0",  "--port", "4000"]
