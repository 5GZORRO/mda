FROM python:3.7

RUN pip install fastapi uvicorn uuid requests datetime typing

EXPOSE 4500

COPY ./app /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4500"]