# Copyright (c) 2023 구FS, all rights reserved. Subject to the MIT licence in `licence.md`.
import datetime as dt
import dropbox, dropbox.exceptions
import json
from KFSconfig  import KFSconfig
from KFSdropbox import KFSdropbox
from KFSlog     import KFSlog
import logging
import os
import pytz
import requests
import time
from exec_server_command import exec_minecraft_server_command


@KFSlog.timeit
def main() -> None:
    backups_filename: list[str]                             # filename of a backups local, should usually only be 1
    CONFIG: dict[str, str]                                  # dropbox_dest_path, minecraft_server_screen_name, source_path
    CONFIG_CONTENT_DEFAULT: dict[str, str]={                # linux screen name to attach to for server commands
        "dropbox_dest_path": "",
        "minecraft_server_screen_name": "",
        "source_path": "",
    }
    dbx: dropbox.Dropbox                                    # dropbox instance
    DROPBOX_API_CRED: dict[str, str]                        # dropbox API access credentials
    DROPBOX_CONFIG_CONTENT_DEFAULT: dict[str, str]={        # dropbox configuration default content
        "app_key": "",
        "app_secret": "",
        "refresh_token": "",
    }
    dropbox_dest_path_filenames: list[str]                  # in destination path filenames
    KEEP_BACKUPS: int=30                                    # keep this amount of most recent backups
    server_backup_next_default_DT: dt.datetime              # next default backup datetime
    server_backup_next_DT: dt.datetime                      # next actual backup datetime, may be different than default if user overrides
    SERVER_BACKUP_T: dt.time=dt.time(hour=0, minute=0)      # at what time will the backups be made
    shutdown_warnings: list[tuple[float, str]]              # shutdown warning plan

    try:
        CONFIG=json.loads(KFSconfig.load_config("config.json", json.dumps(CONFIG_CONTENT_DEFAULT, indent=4)))
    except FileNotFoundError:
        return
    try:
        DROPBOX_API_CRED=json.loads(KFSconfig.load_config("dropbox_API.json", json.dumps(DROPBOX_CONFIG_CONTENT_DEFAULT, indent=4)))                           # load API credentials
    except FileNotFoundError:
        return
    dbx=dropbox.Dropbox(oauth2_refresh_token=DROPBOX_API_CRED["refresh_token"], app_key=DROPBOX_API_CRED["app_key"], app_secret=DROPBOX_API_CRED["app_secret"]) # create Dropbox instance
    server_restart_command: str=f"screen -S \"{CONFIG['minecraft_server_screen_name']}\" -dm bash -c \"cd ../'2023-04-13 Minecraft Auenland Server'; java -Xms10G -Xmx10G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true -jar 'server.jar' nogui\""


    while True:
        logging.info("--------------------------------------------------")
        logging.info("")    # "next server backup at" line can overwrite itself
        server_backup_next_default_DT=dt.datetime.combine(dt.datetime.now(dt.timezone.utc).date(), SERVER_BACKUP_T) # next backup datetime is by default today at backup time
        server_backup_next_default_DT=pytz.timezone("UTC").localize(server_backup_next_default_DT)                  # make timezone aware
        if server_backup_next_default_DT<dt.datetime.now(dt.timezone.utc):                                          # if already past:
            server_backup_next_default_DT+=dt.timedelta(days=1)                                                     # tomorrow
        with open("server_backup_next_DT.config", "wt") as server_backup_next_file:                                 # write default into file first
            server_backup_next_file.write(server_backup_next_default_DT.strftime("%Y-%m-%dT%H:%M:%S"))
        
        while True:         # determine server_backup_next_DT, but keep it variable until within shutdown plan
            with open("server_backup_next_DT.config", "rt") as server_backup_next_file:
                server_backup_next_DT=dt.datetime.strptime(server_backup_next_file.read(), "%Y-%m-%dT%H:%M:%S")
            server_backup_next_DT=pytz.timezone("UTC").localize(server_backup_next_DT)  # make timezone aware
            logging.info(f"\rNext server backup will be made at {server_backup_next_DT.strftime('%Y-%m-%dT%H:%M:%S')}.")

            shutdown_warnings=[ # shutdown warning plan
                (1000,   f"say Warning: Server will restart at UTC {server_backup_next_DT.strftime('%Y-%m-%dT%H:%M')} for a backup."),
                ( 100,   f"say Warning: Server will restart at UTC {server_backup_next_DT.strftime('%Y-%m-%dT%H:%M')} for a backup."),
                (  50,    "say 50"),
                (  40,    "say 40"),
                (  30,    "say 30"),
                (  20,    "say 20"),
                (  10,    "say 10"),
                (   5,    "say 5"),
                (   4,    "say 4"),
                (   3,    "say 3"),
                (   2,    "say 2"),
                (   1,    "say 1"),
                (   0.5,  "say Shutdown."),
            ]
            if dt.datetime.now(dt.timezone.utc)<server_backup_next_DT-dt.timedelta(seconds=shutdown_warnings[0][0]):    
                time.sleep(5)
                continue
            break   # if within shutdown warning plan: server_backup_next_DT now fixed, begin shutdown warning plan
        logging.info(f"Server backup DT is now fixed to {server_backup_next_DT.strftime('%Y-%m-%dT%H:%M:%S')}.")
            
            
        for shutdown_warning in shutdown_warnings:                                                                  # give shutdown warnings
            while dt.datetime.now(dt.timezone.utc)<server_backup_next_DT-dt.timedelta(seconds=shutdown_warning[0]): # wait until appropiate warning time
                time.sleep(0.1)
            exec_minecraft_server_command(shutdown_warning[1], CONFIG["minecraft_server_screen_name"])              # get warning out
        exec_minecraft_server_command("stop", CONFIG["minecraft_server_screen_name"])                               # shutdown server
        logging.info("Waiting 100s...")
        time.sleep(100)                                                                                             # wait until shutdown process complete
        logging.info("\rWaited 100s.")

        backups_filename=[backup_filename
                          for backup_filename
                          in os.listdir(".")
                          if os.path.isfile(backup_filename)==True and os.path.splitext(backup_filename)==".tar"]   # list already existing backups that remained because upload failed or something
        backups_filename.append(f"{server_backup_next_DT.strftime('%Y-%m-%d %H_%M')} backup.tar")                   # next backup filename is backup datetime .tar
        logging.debug("backup filenames:")
        logging.debug(backups_filename)
        logging.info(f"Executing \"tar cf \"{backups_filename[-1]}\" \"{CONFIG['source_path']}\"\" to compress \"{CONFIG['source_path']}\" into \"{backups_filename[-1]}\"...")
        os.system(f"tar cf \"{backups_filename[-1]}\" \"{CONFIG['source_path']}\"")                  # compress server folder
        logging.info(f"\rExecuted \"tar cf \"{backups_filename[-1]}\" \"{CONFIG['source_path']}\"\" to compress \"{CONFIG['source_path']}\" into \"{backups_filename[-1]}\".")

        logging.info(f"Executing \"{server_restart_command}\" to restart server...")
        os.system(server_restart_command)   # restart server as soon as possible
        logging.info(f"\rExecuted \"{server_restart_command}\" to restart server.")
        
        for backup_filename in backups_filename:    # upload backups
            logging.info(f"Uploading \"{backup_filename}\" to \"{os.path.join('Dropbox', CONFIG['dropbox_dest_path'])}\"...")
            try:
                KFSdropbox.upload_file(dbx, backup_filename, os.path.join(CONFIG["dropbox_dest_path"], backup_filename))
            except (dropbox.exceptions.ApiError, dropbox.exceptions.InternalServerError, requests.exceptions.ConnectionError):
                logging.error(f"Uploading \"{backup_filename}\" to \"{os.path.join('Dropbox', CONFIG['dropbox_dest_path'])}\" failed.")
                continue                            # if failed: don't delete, try again tomorrow
            else:
                logging.info(f"\rUploaded \"{backup_filename}\" to \"{os.path.join('Dropbox', CONFIG['dropbox_dest_path'])}\".")

            logging.info(f"Deleting {backup_filename}...")
            try:
                os.remove(backup_filename)  # clean up
            except PermissionError:
                logging.error(f"Deleting {backup_filename} failed with PermissionError.")
            else:
                logging.info(f"\rDeleted {backup_filename}.")

        logging.info(f"Loading filenames from \"{CONFIG['dropbox_dest_path']}\"...")
        dropbox_dest_path_filenames=[dropbox_dest_path_filename         # backups in dropbox, must be .tar
                                     for dropbox_dest_path_filename
                                     in sorted(KFSdropbox.list_files(dbx, CONFIG["dropbox_dest_path"], not_exist_ok=False))
                                     if os.path.splitext(dropbox_dest_path_filename)[1]==".tar"]    
        logging.info(f"\rLoaded filenames from \"{CONFIG['dropbox_dest_path']}\".")
        logging.debug(dropbox_dest_path_filenames)
        for i in range(len(dropbox_dest_path_filenames)-KEEP_BACKUPS):  # delete backups except newest
            logging.info(f"Deleting \"{os.path.join(CONFIG['dropbox_dest_path'], dropbox_dest_path_filenames[i])}\"...")
            dbx.files_delete_v2(os.path.join(CONFIG["dropbox_dest_path"], dropbox_dest_path_filenames[i]))
            logging.info(f"\rDeleted \"{os.path.join(CONFIG['dropbox_dest_path'], dropbox_dest_path_filenames[i])}\".")