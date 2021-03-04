FROM python:3.7

RUN pip install fastapi uvicorn uuid requests datetime

EXPOSE 3700

COPY ./app /app

CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3700" ] 
