FROM python:3.10.0-buster

WORKDIR /code
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
ENV PYTHONPATH /code/
RUN chmod +x bot.py

CMD [ "/code/bot.py" ]