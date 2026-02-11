import logging
from enum import Enum

from src.action import Action

_logger = logging.getLogger()


class ActionType(str, Enum):
    EXECUTION = "execution"
    REPOSITORY_LOADING = "repository_loading"


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


def filter_actions(exec_actions: list[Action], filter_type: ActionFilterType) -> list[Action]:
    _logger.info(f"Applying filter to the actions: {filter_type}...")

    if not ACTION_FILTER_CRITERIA[filter_type]:
        return exec_actions

    filtered_exec_actions: list[Action] = [
        action
        for action in exec_actions
        if any(
            required_field in action.metrics
            for required_field in ACTION_FILTER_CRITERIA[filter_type]
        )
    ]

    _logger.info(
        f"Filtered {len(filtered_exec_actions)} actions out of a total of {len(exec_actions)}..."
    )
    return filtered_exec_actions
