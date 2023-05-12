#Copyright (c) 2023 구FS, all rights reserved. Subject to the MIT licence in `licence.md`.
import datetime as dt
import dropbox
import json
import KFS.config, KFS.dropbox, KFS.log
import logging
import os
import pytz
import time
from exec_server_command import exec_minecraft_server_command


@KFS.log.timeit
def main(logger: logging.Logger) -> None:
    backup_filename: str                                    #filename of a backup
    CONFIG: dict[str, str]                                  #dropbox_dest_path, minecraft_server_screen_name, source_path
    CONFIG_CONTENT_DEFAULT: dict[str, str]={                #linux screen name to attach to for server commands
        "dropbox_dest_path": "",
        "minecraft_server_screen_name": "",
        "source_path": "",
    }
    dbx: dropbox.Dropbox                                    #dropbox instance
    DROPBOX_API_CRED: dict[str, str]                        #dropbox API access credentials
    DROPBOX_CONFIG_CONTENT_DEFAULT: dict[str, str]={        #dropbox configuration default content
        "app_key": "",
        "app_secret": "",
        "refresh_token": "",
    }
    dropbox_dest_path_filenames: list[str]                  #in destination path filenames
    KEEP_BACKUPS: int=30                                    #keep this amount of most recent backups
    server_backup_next_DT: dt.datetime                      #next backup datetime
    SERVER_BACKUP_T: dt.time=dt.time(hour=0, minute=0)      #at what time will the backups be made
    shutdown_warnings: list[tuple[float, str]]              #shutdown warning plan

    try:
        CONFIG=json.loads(KFS.config.load_config("minecraft server dropbox backup creator.json", json.dumps(CONFIG_CONTENT_DEFAULT, indent=4)))
    except FileNotFoundError:
        return
    try:
        DROPBOX_API_CRED=json.loads(KFS.config.load_config("dropbox_API.json", json.dumps(DROPBOX_CONFIG_CONTENT_DEFAULT, indent=4)))                               #load API credentials
    except FileNotFoundError:
        return
    dbx=dropbox.Dropbox(oauth2_refresh_token=DROPBOX_API_CRED["refresh_token"], app_key=DROPBOX_API_CRED["app_key"], app_secret=DROPBOX_API_CRED["app_secret"]) #create Dropbox instance
    server_restart_command: str=f"screen -S \"{CONFIG['minecraft_server_screen_name']}\" -dm bash -c \"cd ../'2023-04-13 Minecraft Auenland Server'; java -Xms10G -Xmx10G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true -jar 'server.jar' nogui\""


    while True:
        logger.info("--------------------------------------------------")
        server_backup_next_DT=dt.datetime.combine(dt.datetime.now(dt.timezone.utc).date(), SERVER_BACKUP_T) #next backup datetime today at backup time
        server_backup_next_DT=pytz.timezone("UTC").localize(server_backup_next_DT)                          #make timezone aware
        if server_backup_next_DT<dt.datetime.now(dt.timezone.utc):                                          #if already past:
            server_backup_next_DT+=dt.timedelta(days=1)                                                     #tomorrow
        logger.info(f"next server backup at: {server_backup_next_DT.strftime('%Y-%m-%dT%H:%M')}")
        
        shutdown_warnings=[ #shutdown warning plan
            (1000,   f"say Warning: Server will restart at UTC {server_backup_next_DT.strftime('%Y-%m-%dT%H:%M')} for its daily backup."),
            ( 100,   f"say Warning: Server will restart at UTC {server_backup_next_DT.strftime('%Y-%m-%dT%H:%M')} for its daily backup."),
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
        for shutdown_warning in shutdown_warnings:                                                                  #make shutdown warnings beforehand
            while dt.datetime.now(dt.timezone.utc)<server_backup_next_DT-dt.timedelta(seconds=shutdown_warning[0]): #wait until appropiate warning time
                time.sleep(0.1)
            exec_minecraft_server_command(shutdown_warning[1], CONFIG["minecraft_server_screen_name"], logger)      #get warning out
        exec_minecraft_server_command("stop", CONFIG["minecraft_server_screen_name"], logger)                       #shutdown server
        time.sleep(100)                                                                                             #wait until shutdown process complete

        backup_filename=f"{server_backup_next_DT.strftime('%Y-%m-%d %H_%M')} backup.tar"        #backup filename is backup datetime .tar
        logger.info(f"Executing \"tar cf \"{backup_filename}\" \"{CONFIG['source_path']}\"\" to compress \"{CONFIG['source_path']}\" into \"{backup_filename}\"...")
        os.system(f"tar cf \"{backup_filename}\" \"{CONFIG['source_path']}\"")                  #compress server folder
        logger.info(f"\rExecuted \"tar cf \"{backup_filename}\" \"{CONFIG['source_path']}\"\" to compress \"{CONFIG['source_path']}\" into \"{backup_filename}\".")

        logger.info(f"Executing \"{server_restart_command}\" to restart server...")
        os.system(server_restart_command)   #restart server as soon as possible
        logger.info(f"\rExecuted \"{server_restart_command}\" to restart server.")

        logger.info(f"Uploading \"{backup_filename}\" to \"{os.path.join('Dropbox', CONFIG['dropbox_dest_path'])}\"...")
        KFS.dropbox.upload_file(dbx, backup_filename, os.path.join(CONFIG["dropbox_dest_path"], backup_filename))   #upload backup
        logger.info(f"\rUploaded \"{backup_filename}\" to \"{os.path.join('Dropbox', CONFIG['dropbox_dest_path'])}\".")

        logger.info(f"Deleting {backup_filename}...")
        try:
            os.remove(backup_filename)  #clean up
        except PermissionError:
            logger.error(f"Deleting {backup_filename} failed with PermissionError.")
        else:
            logger.info(f"\rDeleted {backup_filename}.")

        logger.info(f"Loading filenames from \"{CONFIG['dropbox_dest_path']}\"...")
        dropbox_dest_path_filenames=[dropbox_dest_path_filename #backups in dropbox, must be file and .tar
                                     for dropbox_dest_path_filename
                                     in sorted(KFS.dropbox.list_files(dbx, CONFIG["dropbox_dest_path"], not_exist_ok=False))
                                     if os.path.isfile(dropbox_dest_path_filename)==True and os.path.splitext(dropbox_dest_path_filename)==".tar"]    
        logger.info(f"\rLoaded filenames from \"{CONFIG['dropbox_dest_path']}\".")
        logger.debug(dropbox_dest_path_filenames)
        for i in range(len(dropbox_dest_path_filenames)-KEEP_BACKUPS):  #delete backups except newest
            logger.debug(f"Deleting \"{os.path.join(CONFIG['dropbox_dest_path'], dropbox_dest_path_filenames[i])}\"...")
            dbx.files_delete_v2(os.path.join(CONFIG["dropbox_dest_path"], dropbox_dest_path_filenames[i]))
            logger.debug(f"\rDeleted \"{os.path.join(CONFIG['dropbox_dest_path'], dropbox_dest_path_filenames[i])}\".")