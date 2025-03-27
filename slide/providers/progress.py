from enum import Enum
from threading import Lock
from rich.progress import (
    Progress,
    TimeElapsedColumn,
    TextColumn,
    SpinnerColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from rich.console import Console
from rich.rule import Rule
from rich.console import Group
from rich.live import Live

from slide.logger import Logger

logging = Logger()

class ProgressType(Enum):
    LABEL = "LABEL"
    STEP_TIMED = "STEP_TIMED"
    STEP = "STEP"
    DOWNLOAD = "DOWNLOAD"
    TASK = "TASK"
    OVERALL = "OVERALL"

class ProgressProvider:
    
    _instance = None
    _lock = Lock()  # Thread-safe initialization
        
    label_progress = Progress(
    TimeElapsedColumn(),
    TextColumn('{task.description}'),
    #console=logging.console
    )

    # progress for a task step that takes a while, but we're not sure how long
    step_progress_timed = Progress(
        TextColumn('  '),
        TimeElapsedColumn(),
        TextColumn('[bold purple]{task.fields[action]} ({task.completed}/{task.total})'),
        TimeRemainingColumn(),
        SpinnerColumn('simpleDots'),
        #console=logging.console
    )
    # progress for a task step that has a known total target (steps, bytes, ...)
    step_progress = Progress(
        TextColumn('  '),
        TimeElapsedColumn(),
        TextColumn('[bold purple]{task.fields[action]}'),
        BarColumn(),
        TextColumn('({task.completed}/{task.total})'),
        #console=logging.console
    )
    download_progress = Progress(
        TextColumn('[bold yellow]   Downloading {task.fields[filename]}'),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        #console=logging.console
    )
    # progress for a single tasks
    task_progress = Progress(
        TextColumn('[bold blue]Progress for {task.fields[name]}: {task.percentage:.0f}%'),
        BarColumn(),
        TextColumn('({task.completed} of {task.total} steps done)'),
        #console=logging.console
    )
    overall_progress = Progress(
        SpinnerColumn(),
        TimeElapsedColumn(),
        BarColumn(bar_width=None),
        TextColumn('{task.description}'),
        #console=logging.console,
        expand=True
    )
    group = Group(
        label_progress,
        step_progress_timed,
        step_progress,
        download_progress,
        Rule(style='#AAAAAA'),
        task_progress,
        overall_progress
    )
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return  # Prevent re-initialization
        self._initialized = True
    
    def get_live(self):
        return Live(self.group, console=Console(stderr=True))
    
    def get_progress(self, progress_type: ProgressType):
       match progress_type:
            case ProgressType.LABEL:
                return self.label_progress
            case ProgressType.STEP_TIMED:
                return self.step_progress_timed
            case ProgressType.STEP:
                return self.step_progress
            case ProgressType.DOWNLOAD:
                return self.download_progress
            case ProgressType.TASK:
                return self.task_progress
            case ProgressType.OVERALL:
                return self.overall_progress
            case _:
                raise ValueError(f"Invalid progress type: {progress_type}")