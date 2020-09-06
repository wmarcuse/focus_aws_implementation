import pika
import os
import json
import logging
from collections import defaultdict
from uuid import uuid4

class ModelDataFetcher:
    def __init__(self):
        self.fetched_read_model_data = None

    # Loop trough de provided DynamoDB model data and assign the records to a dictionary
    def get_model_data(self, items):
        # loop through the returned models
        model_list = defaultdict(list)

        for item in items:
            model = {}

            model["modelId"] = item["modelId"]["S"]
            model["name"] = item["name"]["S"]
            model["createdAt"] = item["createdAt"]["S"]
            model["bucketUri"] = item["bucketUri"]["S"]
            model["trainingAccuracy"] = int(item["trainingAccuracy"]["N"])
            model["isThisAwesome"] = bool(item["isThisAwesome"]["BOOL"])

            model_list["models"].append(model)

        return model_list

    def on_message(self, channel, basic_deliver, properties, body):
        response = json.loads(body)
        self.fetched_read_model_data = self.get_model_data(response['Items'])
        channel.close()

    # This method is used at the frontend service /models page.
    def get_all_models(self):
        if os.environ.get('AWS_APP_CONTEXT') == 'DEVELOPMENT_MACHINE':
            # Local testing RabbitMQ credentials
            credentials = pika.PlainCredentials('guest', 'guest')
            parameters = pika.ConnectionParameters('host.docker.internal', credentials=credentials)
        else:
            # CloudAMQP production RabbitMQ credentials
            credentials = pika.PlainCredentials('rmmdazid', '9JK3bJRNEPAYz5sYFk8v3HQdbx7m-BFO')
            parameters = pika.ConnectionParameters('sparrow.rmq.cloudamqp.com/rmmdazid', credentials=credentials)
        connection = pika.BlockingConnection(parameters)
        channel_p = connection.channel()
        channel_p.exchange_declare(
            exchange="model_exchange",
            exchange_type="topic",
            passive=False,
            durable=True,
            auto_delete=False)

        # Assign unique id for unique callback queue tunnel
        specific_callback_id = str(uuid4())

        channel_c = connection.channel()
        queue_name = 'callback_{ID}'.format(ID=specific_callback_id)
        channel_c.queue_declare(
            queue=queue_name,
            auto_delete=False
        )
        channel_c.queue_bind(
            queue=queue_name,
            exchange='model_exchange',
            routing_key=specific_callback_id
        )
        channel_c.basic_qos(prefetch_count=1)

        # Publish the READ request on the broker
        channel_p.basic_publish(
            exchange='model_exchange',
            routing_key='dynamodb.model.crud',
            body=json.dumps({
                'event': 'readModel',
                'context': {
                    'callback_routing_key': specific_callback_id
                }
            }),
            properties=pika.BasicProperties(content_type='application/json', delivery_mode=1))
        channel_p.close()


        channel_c.basic_consume(
            queue=queue_name,
            on_message_callback=self.on_message
        )
        channel_c.start_consuming()
        connection.close()


