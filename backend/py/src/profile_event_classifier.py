import re
from enum import Enum

PROFILE_TS_REGEX = re.compile(r"ts\":(\d+)").search
PROFILE_DUR_REGEX = re.compile(r"dur\":(\d+)").search
PROFILE_TID_REGEX = re.compile(r"tid\":(\d+)").search

PROFILE_CRITICAL_PATH_REGEX = re.compile(r"\"name\":\"Critical Path\"").search
PROFILE_MAIN_THREAD_REGEX = re.compile(r"\"name\":\"Main Thread\"").search
PROFILE_RESOURCES_REGEX = re.compile(r"\"name\":\"collect-local-resources\"").search
PROFILE_GC_REGEX = re.compile(r"\"name\":\"Garbage Collector\"").search
PROFILE_TREE_DELETER = re.compile(r"\"name\":\"tree-deleter\"").search


class PECat(str, Enum):
    ACTION_DEPENDENCY_CHECKING = "action dependency checking"
    ACTION_PROCESSING = "action processing"
    FETCHING_REPOSITORY = "Fetching repository"
    GENERAL_INFORMATION = "general information"
    PACKAGE_CREATION = "package creation"
    LOCAL_ACTION_EXECUTION = "local action execution"
    LOCAL_ACTION_EXECUTION_WALL_TIME = "Local execution process wall time"
    ACTION_RESOURCE_LOCK = "action resource lock"
    ACTION_RESOURCE_RELEASE = "action resource release"
    UPDATE_ACTION_INFORMATION = "update action information"
    STARLARK_BUILT_IN_FUNCTION_CALL = "Starlark builtin function call"
    STARLARK_REPOSITORY_FUNCTION_CALL = "Starlark repository function call"
    STARLARK_USER_FUNCTION_CALL = "Starlark user function call"
    BAZEL_MODULE_PROCESSING = "bazel module processing"
    UNKNOWN = "Unknown event"


class PEName(str, Enum):
    ACTION_POSTPROCESSING = "postprocessing.run"
    CHECK_OUTPUTS = "checkOutputs"
    DISCOVER_INPUTS = "discoverInputs"


class PEClassifier:
    @staticmethod
    def is_action_processing_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.ACTION_PROCESSING

    @staticmethod
    def is_action_dependency_checking_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.ACTION_DEPENDENCY_CHECKING

    @staticmethod
    def is_action_post_processing_run_event(event: dict[str, str]) -> bool:
        return (
            event["cat"] == PECat.GENERAL_INFORMATION
            and event["name"] == PEName.ACTION_POSTPROCESSING
        )

    @staticmethod
    def is_specific_general_information_event(event: dict[str, str], event_name: PEName) -> bool:
        return event["cat"] == PECat.GENERAL_INFORMATION and event["name"] == event_name

    @staticmethod
    def is_package_creation_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.PACKAGE_CREATION

    @staticmethod
    def is_check_outputs_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.GENERAL_INFORMATION and event["name"] == PEName.CHECK_OUTPUTS

    @staticmethod
    def is_discover_inputs_event(event: dict[str, str]) -> bool:
        return event["name"] == PEName.DISCOVER_INPUTS

    @staticmethod
    def is_starlark_repository_function_call_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.STARLARK_REPOSITORY_FUNCTION_CALL

    @staticmethod
    def is_bazel_module_processing_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.BAZEL_MODULE_PROCESSING

    @staticmethod
    def is_starlark_built_in_function_call_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.STARLARK_BUILT_IN_FUNCTION_CALL

    @staticmethod
    def is_local_action_execution_event(event: dict[str, str]) -> bool:
        return (
            event["cat"] == PECat.LOCAL_ACTION_EXECUTION
            or event["cat"] == PECat.LOCAL_ACTION_EXECUTION_WALL_TIME
        )

    @staticmethod
    def is_action_resource_event(event: dict[str, str]) -> bool:
        return (
            event["cat"] == PECat.ACTION_RESOURCE_LOCK
            or event["cat"] == PECat.ACTION_RESOURCE_RELEASE
        )

    @staticmethod
    def is_update_action_information_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.UPDATE_ACTION_INFORMATION

    @staticmethod
    def is_fetching_repository_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.FETCHING_REPOSITORY or (
            event["cat"] == PECat.GENERAL_INFORMATION
            and (event["name"].startswith("fetching: ") or event["name"].startswith("extracting: "))
        )

    @staticmethod
    def is_unknown_event(event: dict[str, str]) -> bool:
        return event["cat"] == PECat.UNKNOWN

    @staticmethod
    def get_event_name(event: dict[str, str]) -> str:
        if (
            PEClassifier.is_local_action_execution_event(event)
            or PEClassifier.is_action_resource_event(event)
            or PEClassifier.is_update_action_information_event(event)
            or PEClassifier.is_action_dependency_checking_event(event)
            or PEClassifier.is_unknown_event(event)
        ):
            # For these event types, the event name is actually in the `cat` field
            return event["cat"].replace(" ", "_")
        else:
            return event["name"].replace(" ", "_")
