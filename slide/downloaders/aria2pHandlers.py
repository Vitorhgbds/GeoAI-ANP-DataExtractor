# ~/callbacks.py
import subprocess
import aria2p


errors = {}

def on_download_error(api: aria2p.API, gid):
    # pop a desktop notification using notify-send
    download = api.get_download(gid)
    summary = f"A download failed"
    body = f"{download.name}\n{download.error_message} (code: {download.error_code})."
    subprocess.call(["notify-send", "-t", "10000", summary, body])
    errors[download.name] = errors.get(download.name, 0) + 1
    if errors[download.name] < 3:
        api.retry_downloads([download])
    else:
        download.purge()


def on_download_complete(api: aria2p.API, gid):
    download = api.get_download(gid)
    download.purge()