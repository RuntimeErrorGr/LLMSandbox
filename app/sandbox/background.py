import threading
from collections.abc import Callable


def start(target: Callable, *args) -> None:
    threading.Thread(target=target, args=args, daemon=True).start()
