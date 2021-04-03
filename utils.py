from time import time

class showTime:
    def __init__(self, *args) -> None:
        print(*args, end=' ', flush=True)
    def __enter__(self) -> None:
        self.__start = time()
    def __exit__(self, *_) -> None:
        self.__end = time()
        print(f"{self.__end - self.__start:.2f}s")
