import pika
from environs import Env

env = Env()
env.read_env()

credentials = pika.PlainCredentials(
    username=env.str('RABBITMQ_DEFAULT_USER'), 
    password=env.str('RABBITMQ_DEFAULT_PASS'),
)
connection = pika.BlockingConnection(pika.ConnectionParameters(
    host=env.str('RABBITMQ_HOST'), 
    port=env.str('RABBITMQ_PORT'),
    credentials=credentials,
))
channel = connection.channel()
channel.queue_declare(queue='hello')
channel.basic_publish(exchange='',
                      routing_key='hello',
                      body='Hello World!')
print(" [x] Sent 'Hello World!'")
connection.close()