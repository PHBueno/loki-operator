FROM python:3.8-slim

WORKDIR /app

COPY ./src /app/src

RUN pip install -r ./src/requirements.txt

CMD [ "kopf", "run", "./src/operator.py", "-n loki-operator", "--verbose" ]