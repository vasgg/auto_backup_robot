from json import loads
import logging.config
from os import chmod, getenv, path, remove
from pathlib import Path
from asyncio import sleep, run
from sys import stderr, stdout
from urllib import parse, request
import zipfile
from datetime import datetime

from paramiko import AutoAddPolicy, SSHClient

TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(getenv("TELEGRAM_CHAT_ID"))
SSH_HOST = getenv("SSH_HOST")
SSH_USER = getenv("SSH_USER")
SSH_KEY_CONTENT = getenv("SSH_KEY")
FILES = loads(getenv("FILES"))


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created).astimezone()
        if datefmt:
            base_time = ct.strftime("%d.%m.%Y %H:%M:%S")
            msecs = f"{int(record.msecs):03d}"
            tz = ct.strftime("%z")
            return f"{base_time}.{msecs}{tz}"
        return super().formatTime(record, datefmt)


main_template = {
    "format": "%(asctime)s | %(message)s",
    "datefmt": "%d.%m.%Y %H:%M:%S%z",
}
error_template = {
    "format": "%(asctime)s [%(levelname)8s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
    "datefmt": "%d.%m.%Y %H:%M:%S%z",
}


def get_logging_config():
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "main": {
                "()": CustomFormatter,
                "format": main_template["format"],
                "datefmt": main_template["datefmt"],
            },
            "errors": {
                "()": CustomFormatter,
                "format": error_template["format"],
                "datefmt": error_template["datefmt"],
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "main",
                "stream": stdout,
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "errors",
                "stream": stderr,
            },
        },
        "loggers": {
            "root": {
                "level": "DEBUG",
                "handlers": ["stdout", "stderr"],
            },
        },
    }


logging_config = get_logging_config()
logging.config.dictConfig(logging_config)


def send_document(file_path: Path, caption: str = ""):
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
        f"sendDocument?chat_id={TELEGRAM_CHAT_ID}&caption={parse.quote(caption)}"
    )
    with file_path.open("rb") as file:
        file_data = file.read()

    boundary = "---BOUNDARY---"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    data = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="{file_path.name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + file_data
        + f"\r\n--{boundary}--\r\n".encode()
    )

    req = request.Request(url, data=data, headers=headers)
    with request.urlopen(req) as response:
        if response.status != 200:
            raise Exception(f"Error sending document: {response.read().decode()}")


async def daily_routine():
    ssh_key_path = "/tmp/script_ssh_key"
    if SSH_KEY_CONTENT:
        with open(ssh_key_path, "w") as key_file:
            key_file.write(SSH_KEY_CONTENT)
        chmod(ssh_key_path, 0o600)

    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, key_filename=ssh_key_path)

    sftp = ssh.open_sftp()

    for description, file_path in FILES.items():
        try:
            try:
                sftp.stat(file_path)
            except FileNotFoundError:
                logging.warning(f"File {file_path} not found, skipping...")
                continue

            local_file_path = Path("/tmp") / Path(file_path).name
            sftp.get(file_path, str(local_file_path))

            if local_file_path.suffix == ".db":
                zip_file_path = local_file_path.with_suffix(".zip")
                with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(local_file_path, arcname=local_file_path.name)
                remove(local_file_path)
                local_file_path = zip_file_path

            send_document(local_file_path, f"Project: {description}")

            remove(local_file_path)
            await sleep(1)

        except Exception as e:
            logging.error(f"Error with {file_path}: {e}", exc_info=True)

    sftp.close()
    ssh.close()

    if path.exists(ssh_key_path):
        remove(ssh_key_path)


async def main():
    await daily_routine()


if __name__ == "__main__":
    run(main())
