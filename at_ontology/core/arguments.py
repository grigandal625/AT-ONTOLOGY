import argparse
import os


def get_args() -> dict:
    # Argument parser setup
    parser = argparse.ArgumentParser(prog="at-ontology", description="Base server for at-ontology")
    parser.add_argument(
        "-u", "--url", help="RabbitMQ URL to connect", required=False, default=os.getenv("RABBIT_MQ_URL", None)
    )
    parser.add_argument(
        "-H",
        "--host",
        help="RabbitMQ host to connect",
        required=False,
        default=os.getenv("RABBIT_MQ_HOST", "localhost"),
    )
    parser.add_argument(
        "-p",
        "--port",
        help="RabbitMQ port to connect",
        required=False,
        default=int(os.getenv("RABBIT_MQ_HOST", 5672)),
        type=int,
    )
    parser.add_argument(
        "-L",
        "--login",
        "-U",
        "--user",
        "--user-name",
        "--username",
        "--user_name",
        dest="login",
        help="RabbitMQ login to connect",
        required=False,
        default=os.getenv("RABBIT_MQ_USER", "guest"),
    )
    parser.add_argument(
        "-P",
        "--password",
        help="RabbitMQ password to connect",
        required=False,
        default=os.getenv("RABBIT_MQ_PASS", "guest"),
    )
    parser.add_argument(
        "-v",
        "--virtualhost",
        "--virtual-host",
        "--virtual_host",
        dest="virtualhost",
        help="RabbitMQ virtual host to connect",
        required=False,
        default=os.getenv("RABBIT_MQ_VIRTUALHOST", "/"),
    )

    parser.add_argument(
        "-sh",
        "--server-host",
        dest="server_host",
        help="Server host",
        required=False,
        default=os.getenv("AT_ONTOLOGY_HOST", "localhost"),
    )

    parser.add_argument(
        "-sp",
        "--server-port",
        dest="server_port",
        help="Server port",
        required=False,
        default=int(os.getenv("AT_ONTOLOGY_PORT", 8000)),
        type=int,
    )

    # DB_ENGINE
    parser.add_argument(
        "-db",
        "--db-engine",
        dest="db_engine",
        help="Database engine",
        required=False,
        default=os.getenv("DB_ENGINE", "postgres"),
        choices=["postgres", "sqlite"],
    )

    # DB_NAME
    parser.add_argument(
        "-dbname",
        "--db-name",
        dest="db_name",
        help="Database name (or database path for sqlite engine)",
        required=False,
        default=os.getenv("DB_NAME", "at_ontology"),
    )

    # DB_USER
    parser.add_argument(
        "-dbuser",
        "--db-user",
        dest="db_user",
        help="Database user",
        required=False,
        default=os.getenv("DB_USER", "at_ontology"),
    )

    # DB_PASSWORD
    parser.add_argument(
        "-dbpass",
        "--db-password",
        dest="db_password",
        help="Database password",
        required=False,
        default=os.getenv("DB_PASS", None),
    )

    # DB_HOST
    parser.add_argument(
        "-dbh",
        "--db-host",
        dest="db_host",
        help="Database host",
        required=False,
        default=os.getenv("DB_HOST", "postgres"),
    )

    # DB_PORT
    parser.add_argument(
        "-dbpt",
        "--db-port",
        dest="db_port",
        help="Database port",
        required=False,
        default=int(os.getenv("DB_PORT", 5432)),
        type=int,
    )

    args = parser.parse_args()
    res = vars(args)
    return res


ARGS_TO_ENV_MAPPING = {
    "url": "RABBIT_MQ_URL",
    "host": "RABBIT_MQ_HOST",
    "port": "RABBIT_MQ_PORT",
    "login": "RABBIT_MQ_USER",
    "password": "RABBIT_MQ_PASS",
    "virtualhost": "RABBIT_MQ_VIRTUALHOST",
    "server_host": "AT_ONTOLOGY_HOST",
    "server_port": "AT_ONTOLOGY_PORT",
    "db_engine": "DB_ENGINE",
    "db_host": "DB_HOST",
    "db_port": "DB_PORT",
    "db_name": "DB_NAME",
    "db_user": "DB_USER",
    "db_password": "DB_PASS",
    "no_worker": "NO_WORKER",
}
