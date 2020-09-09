import pika
import os
import json
import logging
from collections import defaultdict
from uuid import uuid4


# Model data fetcher object responsible for sending a readModel event,
# creating a specific ID bound callback queue (tunnel) and listen
# There for the response
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

    # This method is called when the callback tunnel queue receives the
    # requested model data
    def on_message(self, channel, basic_deliver, properties, body):
        # Parse the message body that is received in the callback queue
        response = json.loads(body)

        # Make the DynamoDB data readable
        self.fetched_read_model_data = self.get_model_data(response['Items'])

        # Acknowledge the message to RabbitMQ
        channel.basic_ack(delivery_tag=basic_deliver.delivery_tag)

        # Close the consumer channel from the get_all_models() method
        channel.close()

    # This method is used at the frontend service /models page on loading the page
    # with every load of refresh the data is fetched via the backend service
    def get_all_models(self):
        if os.environ.get('AWS_APP_CONTEXT') == 'DEVELOPMENT_MACHINE':
            # Local testing RabbitMQ credentials
            amqp_url = 'amqp://guest:guest@host.docker.internal'
        else:
            # CloudAMQP production RabbitMQ credentials
            amqp_url = 'amqps://rmmdazid:9JK3bJRNEPAYz5sYFk8v3HQdbx7m-BFO@sparrow.rmq.cloudamqp.com/rmmdazid'
        connection = pika.BlockingConnection(parameters=pika.URLParameters(amqp_url))

        # Assign producer channel and set exchange
        channel_p = connection.channel()
        channel_p.exchange_declare(
            exchange="model_exchange",
            exchange_type="topic",
            passive=False,
            durable=True,
            auto_delete=False)

        # Assign unique id for unique callback queue tunnel
        specific_callback_id = str(uuid4())

        # Assign consumer channel and callback queue (tunnel)
        channel_c = connection.channel()
        queue_name = 'callback_{ID}'.format(ID=specific_callback_id)
        channel_c.queue_declare(
            queue=queue_name,
            # Delete the queue after the callback tunnel served its purpose
            auto_delete=True
        )

        # Bind the callback queue to the callback id and exchange
        channel_c.queue_bind(
            queue=queue_name,
            exchange='model_exchange',
            routing_key=specific_callback_id
        )
        channel_c.basic_qos(prefetch_count=1)

        # Publish the readModel request to the broker
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

        # Close the producer channel
        channel_p.close()

        # Start listening to the callback queue, waiting for the
        # readModel data to arrive
        channel_c.basic_consume(
            queue=queue_name,
            on_message_callback=self.on_message
        )
        channel_c.start_consuming()

        # Close the connection
        connection.close()


