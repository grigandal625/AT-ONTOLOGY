import pika
import sys
import os
from environs import Env

env = Env()
env.read_env()

credentials = pika.PlainCredentials(
    username=env.str('RABBITMQ_DEFAULT_USER'),
    password=env.str('RABBITMQ_DEFAULT_PASS'),
)


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=env.str('RABBITMQ_HOST'),
        port=env.str('RABBITMQ_PORT'),
        credentials=credentials,
    ))
    channel = connection.channel()
    channel.queue_declare(queue='hello')

    def callback(ch, method, properties, body):
        print(" [x] Received %r" % body)

    channel.basic_consume(queue='hello',
                          auto_ack=True,
                          on_message_callback=callback)
    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
