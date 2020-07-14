FROM python:3.8.4-slim

WORKDIR '/twitterwipe'

ENV COMMAND=''
ENV ARGS=''
ENV APP_KEY=''
ENV APP_SECRET=''
ENV CONSUMER_KEY=''
ENV CONSUMER_SECRET=''
ENV TZ=''

COPY . .

RUN ["pip", "install", "-r", "requirements.txt"]

ENTRYPOINT python3 twitterwipe.py $COMMAND $ARGS


