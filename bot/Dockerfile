FROM python:3.9.5-slim

RUN mkdir -p /home/app

RUN addgroup --system app && adduser --system --group app

ENV HOME=/home/app
WORKDIR $HOME

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
COPY ./requirements/bot.txt $HOME/requirements.txt
RUN pip install -r requirements.txt

COPY ./bot $HOME

RUN chown -R app:app $HOME

USER app
