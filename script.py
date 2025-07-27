from json import loads
from os import chmod, getenv, path, remove
from pathlib import Path
from asyncio import sleep, run
import zipfile

import paramiko
from aiogram import Bot
from aiogram.types import FSInputFile

TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(getenv("TELEGRAM_CHAT_ID"))
SSH_HOST = getenv("SSH_HOST")
SSH_USER = getenv("SSH_USER")
SSH_KEY_CONTENT = getenv("SSH_KEY")
FILES = loads(getenv("FILES"))

bot = Bot(token=TELEGRAM_TOKEN)


async def send_files_to_group():
    ssh_key_path = "/tmp/script_ssh_key"
    if SSH_KEY_CONTENT:
        with open(ssh_key_path, "w") as key_file:
            key_file.write(SSH_KEY_CONTENT)
        chmod(ssh_key_path, 0o600)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, key_filename=ssh_key_path)

    sftp = ssh.open_sftp()

    for description, file_path in FILES.items():
        try:
            try:
                sftp.stat(file_path)
            except FileNotFoundError:
                print(f"File {file_path} not found")
                continue

            local_file_path = Path("/tmp") / Path(file_path).name
            sftp.get(file_path, str(local_file_path))

            if local_file_path.suffix == ".db":
                zip_file_path = local_file_path.with_suffix(".zip")
                with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(local_file_path, arcname=local_file_path.name)
                remove(local_file_path)
                local_file_path = zip_file_path

            file_to_send = FSInputFile(local_file_path)
            await bot.send_document(
                TELEGRAM_CHAT_ID,
                document=file_to_send,
                caption=f"Project: {description}",
            )

            remove(local_file_path)
            await sleep(1)

        except Exception as e:
            print(f"Error with {file_path}: {e}")

    sftp.close()
    ssh.close()

    if path.exists(ssh_key_path):
        remove(ssh_key_path)


async def main():
    await send_files_to_group()

if __name__ == "__main__":
    run(main())
