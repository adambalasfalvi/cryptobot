import threading
import queue

class ExceptionThread(threading.Thread):
    """
    A thread class that captures exceptions raised in the thread and puts them in a provided exception queue.
    Attributes:
        exception_queue (queue.Queue): A queue to store exceptions raised in the thread.
    Methods:
        run():
            Executes the target function of the thread and captures any exceptions, placing them in the exception queue.
    """
    def __init__(self, *args, **kwargs):
        self.exception_queue : queue = kwargs.pop('exception_queue')
        super().__init__(*args, **kwargs)

    def run(self):
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)
        except Exception as e:
            self.exception_queue.put((self.name, e))