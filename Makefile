rabbit:
	sudo docker run -d --env-file=".env" --hostname my-rabbit --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.10-management