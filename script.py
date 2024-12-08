import os
from pathlib import Path
import asyncio
import paramiko
from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

SSH_HOST = os.getenv("SSH_HOST")
SSH_PORT = int(os.getenv("SSH_PORT", 22))
SSH_USER = os.getenv("SSH_USER")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

BASE_DIRS = ["/path/to/folder1", "/path/to/folder2"]

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


async def find_and_send_files():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, key_filename=SSH_KEY_PATH)

    for base_dir in BASE_DIRS:
        folder_name = base_dir.rstrip("/").split("/")[-1]
        stdin, stdout, stderr = ssh.exec_command(f"find {base_dir} -type f \\( -name '*.sql' -o -name '*.db' \\)")
        files = stdout.read().decode().strip().split("\n")

        for file_path in files:
            if not file_path:
                continue

            local_file_path = Path("/tmp") / Path(file_path).name
            sftp = ssh.open_sftp()
            sftp.get(file_path, str(local_file_path))
            sftp.close()

            file_to_send = FSInputFile(local_file_path)
            await bot.send_document(
                TELEGRAM_CHAT_ID,
                document=file_to_send,
                caption=f"Файл из папки: {folder_name}",
            )

    ssh.close()


async def main():
    await find_and_send_files()


if __name__ == "__main__":
    asyncio.run(main())
