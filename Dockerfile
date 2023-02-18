FROM python:3.10-slim
WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip3 install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code

CMD [ "python3", "/code/start-quotes-spider.py" ]
