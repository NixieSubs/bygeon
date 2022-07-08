from threading import Thread
from typing import Callable

def run_in_thread(func: Callable, args: tuple):
    thread = Thread(target=func,args=args)
    thread.start()
