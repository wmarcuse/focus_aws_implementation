import os
from flask import Flask, jsonify, json, Response, request, render_template
from flask_cors import CORS
from model_data import ModelDataFetcher
import json
import pika

# A very basic API created using Flask that has two possible routes for requests.

# app = Flask(__name__, static_url_path=os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__)
CORS(app)

# The service basepath has a short response to ensure that health checks
# sent to the service root will receive a healthy response.
@app.route("/")
def health_check_response():
    return jsonify({"message": "Empty basepath used for health check. Try /models instead."})

# Returns all of the models in DynamoDB, to be displayed on the website.
# The model data is fetched from the ModelDataFetcher which sends event
# messages to RabbitMQ.
@app.route("/models")
def get_models():
    model_data_fetcher = ModelDataFetcher()
    model_data_fetcher.get_all_models()
    flag = None
    while flag is None:
        flag = model_data_fetcher.fetched_read_model_data
    return render_template('index.html', data=flag['models'])

# Sends an updateModel event to RabbitMQ when a button
# to change the awesomeness is clicked
def message_broker_trigger(awesomeness):
    if os.environ.get('AWS_APP_CONTEXT') == 'DEVELOPMENT_MACHINE':
        # Local testing RabbitMQ credentials
        amqp_url = 'amqp://guest:guest@host.docker.internal'
    else:
        # CloudAMQP production RabbitMQ credentials
        amqp_url = 'amqps://rmmdazid:9JK3bJRNEPAYz5sYFk8v3HQdbx7m-BFO@sparrow.rmq.cloudamqp.com/rmmdazid'
    connection = pika.BlockingConnection(parameters=pika.URLParameters(amqp_url))
    channel = connection.channel()
    channel.exchange_declare(
        exchange="model_exchange",
        exchange_type="topic",
        passive=False,
        durable=True,
        auto_delete=False)

    channel.basic_publish(
        exchange='model_exchange',
        routing_key='dynamodb.model.crud',
        body=json.dumps({
            'event': 'updateModel',
            'context': {
                'awesomeness': awesomeness
            }
        }),
        properties=pika.BasicProperties(content_type='application/json', delivery_mode=1))
    connection.close()

# Route for the awesomeness True button
@app.route("/message_broker_trigger_awesome_true")
def awesomeness_true():
    message_broker_trigger(awesomeness=True)
    return 'OK'

# Route for the awesomeness False button
@app.route("/message_broker_trigger_awesome_false")
def awesomeness_false():
    message_broker_trigger(awesomeness=False)
    return 'OK'


# Run the service on the local server it has been deployed to,
# listening on port 8080.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
