from time import time

class showTime:
    def __init__(self, *args, print_until_finished=False) -> None:
        self.to_print = args
        self.print_until_finished = print_until_finished
        if not self.print_until_finished:
            print(*self.to_print, end=' ', flush=True)
    def __enter__(self) -> None:
        self.__start = time()
    def __exit__(self, *_) -> None:
        self.__end = time()
        if self.print_until_finished:
            print(*self.to_print, end=' ')
        print(f"{self.__end - self.__start:.2f}s")
