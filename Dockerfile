FROM python:3.8.4-slim

WORKDIR '/twitterwipe'

COPY . .

RUN ["pip", "install", "-r", "requirements.txt"]

ENTRYPOINT python3 twitterwipe.py $COMMAND $ARGS


