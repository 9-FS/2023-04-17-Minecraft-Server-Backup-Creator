---
Topic: "Minecraft Server Dropbox Backup Creator"
Author: "구FS"
---
<link href="./doc_templates/md_style.css" rel="stylesheet"></link>
<body>

# <p style="text-align: center;">Minecraft Server Dropbox Backup Creator</p>
<br>
<br>

- [1. General](#1-general)

## 1. General

This program automatically creates backups of your minecraft server directory `source_path` that runs in screen `minecraft_server_screen_name` and uploads them to dropbox `dropbox_dest_path`. 

It handles:

1. warning online players about the impeding shutdown
1. shutting down the server
1. compressing `source_path` into a `.tar`
1. restarting the server in `minecraft_server_screen_name`
1. uploading the backup `.tar` into `dropbox_dest_path`
1. removing the local backup `.tar`
1. removing all online backups except the newest `KEEP_BACKUPS`

</body>