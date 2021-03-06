FROM python:3.9-bullseye

ARG SLACK_VERFICATION_KEY
ARG SLACK_CLEINT_TOKEN
ARG MYSQL_HOST
ARG MYSQL_USER
ARG MYSQL_PASSWORD

RUN export ENV="PROD"

COPY . .

RUN pip install -r req.txt

CMD ["python", "main.py"]