import datetime
import json
import logging

from src.profile_event_classifier import ProfileEventTypeClassifier

_logger = logging.getLogger()


class Action:
    def __init__(
        self,
        primary_event: dict[str, str],
        current_index: int,
        event_groups: list[list[str]],
        build_start_time: datetime.datetime,
    ) -> None:
        self.metrics: dict[str, str] = self._build_action(
            primary_event, current_index, event_groups
        )
        self._add_common_metrics(primary_event, build_start_time)

    def _add_common_metrics(
        self, primary_event: dict[str, str], build_start_time: datetime.datetime
    ) -> None:
        self.metrics["name"] = primary_event["name"]
        self.metrics["timestamp"] = datetime.datetime.fromtimestamp(
            build_start_time.timestamp() + (int(primary_event["ts"]) / 1000000)
        ).isoformat()

    def _build_action(
        self,
        primary_event: dict[str, str],
        current_index: int,
        event_groups: list[list[str]],
    ) -> dict[str, str]:
        raise NotImplementedError()


class ExecutionAction(Action):
    def _build_action(
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
        return_dict["mnemonic"] = primary_event.get("args").get("mnemonic")  # type: ignore

        # Check if the prev event group on this thread is related to this one
        if current_index - 1 >= 0:
            prev_primary_event: dict[str, str] = json.loads(event_groups[current_index - 1][0])
            if ProfileEventTypeClassifier.is_action_dependency_checking_event(prev_primary_event):
                prev_primary_event_name = ProfileEventTypeClassifier.get_event_name(
                    prev_primary_event
                )
                return_dict[f"duration.{prev_primary_event_name}"] = prev_primary_event["dur"]
                total_duration += int(prev_primary_event["dur"])

        # Skip the first in the list as that's the primary_event
        for child_event in event_groups[current_index][1:]:
            child_event_dict: dict[str, str] = json.loads(child_event)
            child_event_name = ProfileEventTypeClassifier.get_event_name(child_event_dict)
            return_dict[f"duration.{child_event_name}"] = child_event_dict["dur"]

        # Check if the next event group on this thread is related to this one
        if current_index + 1 < len(event_groups):
            next_primary_event: dict[str, str] = json.loads(event_groups[current_index + 1][0])
            if ProfileEventTypeClassifier.is_action_post_processing_run_event(next_primary_event):
                next_primary_event_name = ProfileEventTypeClassifier.get_event_name(
                    next_primary_event
                )
                return_dict[f"duration.{next_primary_event_name}"] = next_primary_event["dur"]
                total_duration += int(next_primary_event["dur"])

        return_dict["duration.total"] = str(total_duration)

        return return_dict


class RepositoryLoadingAction(Action):
    def _build_action(
        self,
        primary_event: dict[str, str],
        current_index: int,
        event_groups: list[list[str]],
    ) -> dict[str, str]:
        return_dict: dict[str, str] = {}

        return_dict["target"] = primary_event["name"].replace("//external:", "@@")
        return_dict["duration.total"] = primary_event["dur"]

        # Skip the first in the list as that's the primary_event
        for child_event in event_groups[current_index][1:]:
            child_event_dict: dict[str, str] = json.loads(child_event)
            # Note: We only want `Starlark builtin function call` and not `Starlark repository function call` here.
            # `Starlark repository function call` as a child event can contain host-specific data which we don't want
            # to map into an Elasticsearch field, e.g.:
            # {"cat":"Starlark repository function call","name":"local: /home/developer/.cache/bazel/_bazel_developer/install/bd3f2062f72dd67fde166eda94178459/process-wrapper --timeout=600
            # --kill_delay=15 git -c core.fsmonitor=false reset --hard f49d1e11d6bb7d7a9592573e75afbf562e2f5cb9","ph":"X","ts":14967562,"dur":175559,"pid":1,"tid":1000003}']
            if ProfileEventTypeClassifier.is_starlark_built_in_function_call_event(
                child_event_dict
            ):
                child_event_name = ProfileEventTypeClassifier.get_event_name(child_event_dict)
                return_dict[f"duration.{child_event_name}"] = child_event_dict["dur"]

        return return_dict
