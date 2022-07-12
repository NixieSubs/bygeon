from threading import Thread
from typing import Callable
import requests
import os
from pathlib import Path


def run_in_thread(func: Callable, args: tuple):
    thread = Thread(target=func, args=args)
    thread.start()


def download_to_cache(url: str, directory: str, filename: str, headers=None):
    Path(directory).mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        content_type = r.headers["content-type"]

        filename = rename_with_proper_suffix(filename, content_type)

        file_path = os.path.join(directory, filename)
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return file_path


def rename_with_proper_suffix(filename: str, content_type: str) -> str:
    suffix = "." + content_type.split("/")[1]
    if not filename.endswith(suffix):
        filename += suffix
    return filename
