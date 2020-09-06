import os
from flask import Flask, jsonify, json, Response, request, render_template
from flask_cors import CORS
import model_data
import json
import pika

# A very basic API created using Flask that has two possible routes for requests.

# app = Flask(__name__, static_url_path=os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__)
CORS(app)

# The service basepath has a short response to ensure that health checks
# sent to the service root will receive a healthy response.
@app.route("/")
def healthCheckResponse():
    return jsonify({"message": "Empty basepath used for health check. Try /models instead."})

# Returns all of the models in DynamoDB to be displayed on the website.
@app.route("/models")
def get_models():

    model_data_fetcher = model_data.ModelDataFetcher()
    model_data_fetcher.get_all_models()
    flag = None
    while flag is None:
        flag = model_data_fetcher.fetched_read_model_data
    return render_template('index.html', data=flag['models'])


def message_broker_trigger(awesomeness):
    if os.environ.get('AWS_APP_CONTEXT') == 'DEVELOPMENT_MACHINE':
        # Local testing RabbitMQ credentials
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters('host.docker.internal', credentials=credentials)
    else:
        # CloudAMQP production RabbitMQ credentials
        credentials = pika.PlainCredentials('rmmdazid', '9JK3bJRNEPAYz5sYFk8v3HQdbx7m-BFO')
        parameters = pika.ConnectionParameters('sparrow.rmq.cloudamqp.com/rmmdazid', credentials=credentials)
    connection = pika.BlockingConnection(parameters)
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


@app.route("/message_broker_trigger_awesome_true")
def awesomeness_true():
    message_broker_trigger(awesomeness=True)
    return 'OK'


@app.route("/message_broker_trigger_awesome_false")
def awesomeness_false():
    message_broker_trigger(awesomeness=False)
    return 'OK'


# Run the service on the local server it has been deployed to,
# listening on port 8080.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
