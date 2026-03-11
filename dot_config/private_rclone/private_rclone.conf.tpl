[do]
type = s3
provider = DigitalOcean
access_key_id = {{ op://rclone/do/access_key_id }}
secret_access_key = {{ op://rclone/do/secret_access_key }}
endpoint = {{ op://rclone/do/endpoint }}

[media_local]
type = hasher
remote = /mnt/e/media

[media]
type = union
action_policy = all
create_policy = all
search_policy = ff
upstreams = media_local: media_webdav:

[steamdeck]
type = sftp
host = {{ op://rclone/steamdeck/host }}
user = {{ op://rclone/steamdeck/user }}
key_use_agent = true
shell_type = unix
md5sum_command = md5sum
sha1sum_command = sha1sum

[steamdeck_sdvmods]
type = alias
remote = steamdeck:/home/deck/.local/share/Steam/steamapps/common/Stardew Valley/Mods/

[dropbox_personal]
type = dropbox
token = {{ op://rclone/dropbox_personal/token }}

[dropbox_alt]
type = dropbox
token = {{ op://rclone/dropbox_alt/token }}

[media_webdav]
type = webdav
url = {{ op://rclone/media_webdav/url }}
user = {{ op://rclone/media_webdav/user }}
pass = {{ op://rclone/media_webdav/pass }}
vendor = owncloud

[gdrive_personal_shared_with_me]
type = drive
client_id = {{ op://rclone/gdrive_personal/client_id }}
client_secret = {{ op://rclone/gdrive_personal/client_secret }}
token = {{ op://rclone/gdrive_personal/token }}
scope = drive
team_drive =
shared_with_me = true

[gdrive_personal_my_drive]
type = drive
client_id = {{ op://rclone/gdrive_personal/client_id }}
client_secret = {{ op://rclone/gdrive_personal/client_secret }}
token = {{ op://rclone/gdrive_personal/token }}
scope = drive
team_drive =
shared_with_me = false

[gdrive_personal]
type = combine
upstreams = "My Drive=gdrive_personal_my_drive:" "Shared with me=gdrive_personal_shared_with_me:"


[obv_mods]
type = alias
remote = C:\Users\LocalUser\Documents\Oblivion Mods\Overlay

[obv]
type = alias
remote = D:\XboxGames\The Elder Scrolls IV- Oblivion Remastered

[gdrive_alt]
type = combine
upstreams = "My Drive=gdrive_alt_my_drive:" "Shared with me=gdrive_alt_shared_with_me:"

[gdrive_alt_shared_with_me]
type = drive
client_id = {{ op://rclone/gdrive_alt/client_id }}
client_secret = {{ op://rclone/gdrive_alt/client_secret }}
scope = drive
shared_with_me = true
token = {{ op://rclone/gdrive_alt/token }}
team_drive =

[gdrive_alt_my_drive]
type = drive
client_id = {{ op://rclone/gdrive_alt/client_id }}
client_secret = {{ op://rclone/gdrive_alt/client_secret }}
scope = drive
shared_with_me = false
token = {{ op://rclone/gdrive_alt/token }}
team_drive =

[knode1]
type = sftp
host = {{ op://rclone/knode1/host }}
user = personal
shell_type = unix
md5sum_command = md5sum
sha1sum_command = sha1sum

[knode2]
type = sftp
host = {{ op://rclone/knode2/host }}
user = personal
shell_type = unix
md5sum_command = md5sum
sha1sum_command = sha1sum
