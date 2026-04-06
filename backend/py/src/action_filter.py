from enum import Enum


class ActionFilterType(str, Enum):
    ALL = "all"
    EXECUTED = "executed"
    EXECUTED_REMOTELY = "executed_remotely"
    EXECUTED_LOCALLY = "executed_locally"


ACTION_FILTER_CRITERIA: dict[ActionFilterType, list[str]] = {
    ActionFilterType.ALL: [],
    ActionFilterType.EXECUTED: [
        "duration.execute_remotely",  # Remote
        "duration.subprocess.run",  # Linux-sandbox/processwrapper-sandbox
        "duration.local_action_execution",  # Local
    ],
    ActionFilterType.EXECUTED_REMOTELY: ["duration.execute_remotely"],
    ActionFilterType.EXECUTED_LOCALLY: [
        "duration.subprocess.run",
        "duration.local_action_execution",
    ],
}
