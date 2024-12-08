import os
from pathlib import Path
import asyncio
import paramiko
from aiogram import Bot
from aiogram.types import FSInputFile

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_KEY_CONTENT = os.getenv("SSH_KEY")

FILES = {
    "new_praxis": "~/pyprojects/vasg/new_praxis_bot/prod_new_praxis_bot.db",
    "northwest_poker": "~/pyprojects/vasg/northwest_poker/prod_northwest_poker.db",
    "english_buddy": "~/pyprojects/english_buddy_bot/prod_english_buddy.db",
    "seeker_apple": "~/pyprojects/keyword_seeker/apple/database.db",
    "seeker_misha": "~/pyprojects/keyword_seeker/misha/database.db",
    "pole_dance_voter": "~/niko_bot/PoleDanceVoter_git/pgbackups/daily/postgres-latest.sql.gz"
}

bot = Bot(token=TELEGRAM_TOKEN)


async def send_files_to_group():
    ssh_key_path = "/tmp/script_ssh_key"
    if SSH_KEY_CONTENT:
        with open(ssh_key_path, "w") as key_file:
            key_file.write(SSH_KEY_CONTENT)
        os.chmod(ssh_key_path, 0o600)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, username=SSH_USER, key_filename=ssh_key_path)

    sftp = ssh.open_sftp()

    for description, file_path in FILES.items():
        try:
            local_file_path = Path("/tmp") / Path(file_path).name
            sftp.get(file_path, str(local_file_path))

            file_to_send = FSInputFile(local_file_path)
            await bot.send_document(
                TELEGRAM_CHAT_ID,
                document=file_to_send,
                caption=f"Project: {description}",
            )

            os.remove(local_file_path)

        except Exception as e:
            print(f"Ошибка при обработке файла {file_path}: {e}")

    sftp.close()
    ssh.close()

    if os.path.exists(ssh_key_path):
        os.remove(ssh_key_path)


async def main():
    await send_files_to_group()


if __name__ == "__main__":
    asyncio.run(main())
