import datetime
import json
from enum import Enum

from src.profile_event_classifier import PEClassifier


class ActionType(str, Enum):
    EXECUTION = "execution"
    REPOSITORY_LOADING = "repository_loading"
    UNKNOWN = "unknown"
    IGNORED = "ignored"


class Action:
    def __init__(
        self,
        current_index: int,
        event_groups: list[list[str]],
        build_start_time: datetime.datetime,
    ) -> None:
        self.metrics: dict[str, str | int] = {}
        self.build_start_time = build_start_time

        self._build_action(current_index, event_groups)

    def _build_action(self, index: int, event_groups: list[list[str]]) -> None:
        primary_event: dict[str, str] = json.loads(event_groups[index][0])

        self.metrics["name"] = PEClassifier.get_event_name(primary_event)
        self.metrics["cat"] = primary_event["cat"]
        self.metrics["timestamp"] = datetime.datetime.fromtimestamp(
            self.build_start_time.timestamp() + (int(primary_event["ts"]) / 1000000)
        ).isoformat()

        ### Core event types that we are interested in ###
        if PEClassifier.is_action_processing_event(primary_event):
            self.action_type = ActionType.EXECUTION
            self.metrics.update(self._build_execution_action(primary_event, index, event_groups))
        elif PEClassifier.is_starlark_repository_function_call_event(
            primary_event
        ) or PEClassifier.is_bazel_module_processing_event(primary_event):
            self.action_type = ActionType.REPOSITORY_LOADING
            self.metrics.update(self._build_repo_loading_action(primary_event, index, event_groups))

        ### Event types that we are explicitly not interested in ##
        elif (
            # These events are mostly file read operations and are so negligible (under 1ms)
            # that it's definitely not worth tracking them.
            PEClassifier.is_package_creation_event(primary_event)
            or PEClassifier.is_check_outputs_event(primary_event)
            or PEClassifier.is_discover_inputs_event(primary_event)
            ###
            # These events are always associated with an action processing event
            # and are already being tracked in the `_process_execution_event_group` function.
            or PEClassifier.is_action_dependency_checking_event(primary_event)
            or PEClassifier.is_action_post_processing_run_event(primary_event)
            ###
            # A fetching repository event by itself is essentially an event that checks that
            # the bazel external repository is up to date. If the repository is up to date, e.g.
            # it's in the cache, then this event is negligible. If the repository is not up to date,
            # then the event is associated with a starlark repository function call event and
            # is already being tracked in the `_process_repository_loading_event_group` function.
            or PEClassifier.is_fetching_repository_event(primary_event)
        ):
            self.action_type = ActionType.IGNORED

        ### Event types that we do not have any tracking logic for ###
        else:
            self.action_type = ActionType.UNKNOWN

    def _build_execution_action(
        self,
        primary_event: dict[str, str],
        current_index: int,
        event_groups: list[list[str]],
    ) -> dict[str, str]:
        return_dict: dict[str, str] = {}

        total_duration = int(primary_event["dur"])
        # Requires `--experimental_profile_include_target_label`
        return_dict["target"] = primary_event.get("args", {}).get("target", "")  # type: ignore
        # Requires `--experimental_profile_include_primary_output`
        if "out" in primary_event:
            return_dict["out"] = primary_event["out"]
        return_dict["mnemonic"] = primary_event.get("args", {}).get("mnemonic", "")  # type: ignore

        # Check if the prev event group on this thread is related to this one
        if current_index - 1 >= 0:
            prev_primary_event: dict[str, str] = json.loads(event_groups[current_index - 1][0])
            if PEClassifier.is_action_dependency_checking_event(prev_primary_event):
                prev_primary_event_name = PEClassifier.get_event_name(prev_primary_event)
                return_dict[f"duration.{prev_primary_event_name}"] = str(prev_primary_event["dur"])
                total_duration += int(prev_primary_event["dur"])

        # Skip the first in the list as that's the primary_event
        for child_event in event_groups[current_index][1:]:
            child_event_dict: dict[str, str] = json.loads(child_event)
            child_event_name = PEClassifier.get_event_name(child_event_dict)
            return_dict[f"duration.{child_event_name}"] = str(child_event_dict["dur"])

        # Check if the next event group on this thread is related to this one
        if current_index + 1 < len(event_groups):
            next_primary_event: dict[str, str] = json.loads(event_groups[current_index + 1][0])
            if PEClassifier.is_action_post_processing_run_event(next_primary_event):
                next_primary_event_name = PEClassifier.get_event_name(next_primary_event)
                return_dict[f"duration.{next_primary_event_name}"] = str(next_primary_event["dur"])
                total_duration += int(next_primary_event["dur"])

        return_dict["duration.total"] = str(total_duration)

        return return_dict

    def _build_repo_loading_action(
        self,
        primary_event: dict[str, str],
        current_index: int,
        event_groups: list[list[str]],
    ) -> dict[str, str]:
        return_dict: dict[str, str] = {}

        return_dict["target"] = primary_event["name"].replace("//external:", "@@")
        return_dict["duration.total"] = str(primary_event["dur"])

        # Skip the first in the list as that's the primary_event
        for child_event in event_groups[current_index][1:]:
            child_event_dict: dict[str, str] = json.loads(child_event)
            # Note: We only want `Starlark builtin function call` and not `Starlark repository function call` here.
            # `Starlark repository function call` as a child event can contain host-specific data which we don't want
            # to map into an Elasticsearch field, e.g.:
            # {"cat":"Starlark repository function call","name":"local: /home/developer/.cache/bazel/_bazel_developer/install/bd3f2062f72dd67fde166eda94178459/process-wrapper --timeout=600
            # --kill_delay=15 git -c core.fsmonitor=false reset --hard f49d1e11d6bb7d7a9592573e75afbf562e2f5cb9","ph":"X","ts":14967562,"dur":175559,"pid":1,"tid":1000003}']
            if PEClassifier.is_starlark_built_in_function_call_event(child_event_dict):
                child_event_name = PEClassifier.get_event_name(child_event_dict)
                return_dict[f"duration.{child_event_name}"] = str(child_event_dict["dur"])

        return return_dict
