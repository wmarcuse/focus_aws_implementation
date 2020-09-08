FROM python:3.8.3

COPY ./service/requirements.txt /requirements.txt

RUN pip install -r ./requirements.txt

COPY ./service .

ENTRYPOINT ["python"]
CMD ["frontend_service.py"]
