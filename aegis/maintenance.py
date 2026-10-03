"""Exclusive workspace ownership shared by the server and offline restore."""
import fcntl
from pathlib import Path


class WorkspaceBusy(RuntimeError):
    pass


class WorkspaceLease:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.file = (directory / '.server.lock').open('a+')
        try:
            fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise WorkspaceBusy('워크스페이스가 사용 중입니다. 서버를 종료한 후 다시 시도하세요.') from exc

    def close(self):
        if not self.file.closed:
            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
