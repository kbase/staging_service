FROM python:3
# initially built on 3.6.3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install 

CMD [ "python", "./app.py" ]