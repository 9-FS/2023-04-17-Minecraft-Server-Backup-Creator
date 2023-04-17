#Copyright (c) 2023 구FS, all rights reserved. Subject to the MIT licence in `licence.md`.
import logging
import os


def exec_minecraft_server_command(command: str, minecraft_server_screen_name: str, logger: logging.Logger) -> None:
    """
    Execute command in the minecraft server console.

    Arguments:
    - command: command to execute
    - minecraft_server_screen_name: linux screen the server runs in 
    - logger: logger to log to
    """
    logger.info(f"Executing minecraft server command \"{command}\"...")
    os.system(f"screen -S \"{minecraft_server_screen_name}\" -X stuff '{command}\015'")   #jump into screen, execute command, press enter
    logger.info(f"\rExecuted minecraft server command \"{command}\".")
    return

#source: https://github.com/tschuy/minecraft-server-control/blob/master/minecraft.py