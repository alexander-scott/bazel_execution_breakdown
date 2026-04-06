import datetime

from src.action import Action, ActionType
from src.profile_event_classifier import PECat, PEName
from tests.conftest import make_event_str

BUILD_START_TIME = datetime.datetime(2026, 2, 9, 17, 7, 35)


def make_execution_event(ts: int = 1_000_000, dur: int = 5_000_000, **kwargs: object) -> str:
    return make_event_str(
        cat=PECat.ACTION_PROCESSING,
        name="CppCompile my/lib.cpp",
        ts=ts,
        dur=dur,
        args={"target": "//my:lib", "mnemonic": "CppCompile"},
        **kwargs,
    )


def make_repo_loading_event(ts: int = 1_000_000, dur: int = 3_000_000, **kwargs: object) -> str:
    return make_event_str(
        cat=PECat.STARLARK_REPOSITORY_FUNCTION_CALL,
        name="//external:some_repo",
        ts=ts,
        dur=dur,
        **kwargs,
    )


def make_dependency_checking_event(ts: int = 500_000, dur: int = 400_000) -> str:
    return make_event_str(
        cat=PECat.ACTION_DEPENDENCY_CHECKING,
        name="action dependency checking",
        ts=ts,
        dur=dur,
    )


def make_postprocessing_event(ts: int = 6_100_000, dur: int = 200_000) -> str:
    return make_event_str(
        cat=PECat.GENERAL_INFORMATION,
        name=PEName.ACTION_POSTPROCESSING,
        ts=ts,
        dur=dur,
    )


class TestActionTypeClassification:
    def test_given_action_processing_event_when_action_built_expect_execution_type(self) -> None:
        event_groups = [[make_execution_event()]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.EXECUTION

    def test_given_starlark_repo_function_event_when_action_built_expect_repository_loading_type(
        self,
    ) -> None:
        event_groups = [[make_repo_loading_event()]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.REPOSITORY_LOADING

    def test_given_bazel_module_processing_event_when_action_built_expect_repository_loading_type(
        self,
    ) -> None:
        event_str = make_event_str(
            cat=PECat.BAZEL_MODULE_PROCESSING,
            name="some_bzlmod_module",
            ts=1_000_000,
            dur=2_000_000,
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.REPOSITORY_LOADING

    def test_given_package_creation_event_when_action_built_expect_ignored_type(self) -> None:
        event_str = make_event_str(
            cat=PECat.PACKAGE_CREATION, name="some/package", ts=1_000_000, dur=100_000
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.IGNORED

    def test_given_check_outputs_event_when_action_built_expect_ignored_type(self) -> None:
        event_str = make_event_str(
            cat=PECat.GENERAL_INFORMATION,
            name=PEName.CHECK_OUTPUTS,
            ts=1_000_000,
            dur=100_000,
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.IGNORED

    def test_given_discover_inputs_event_when_action_built_expect_ignored_type(self) -> None:
        event_str = make_event_str(
            cat=PECat.GENERAL_INFORMATION,
            name=PEName.DISCOVER_INPUTS,
            ts=1_000_000,
            dur=100_000,
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.IGNORED

    def test_given_action_dependency_checking_event_when_action_built_expect_ignored_type(
        self,
    ) -> None:
        event_str = make_event_str(
            cat=PECat.ACTION_DEPENDENCY_CHECKING,
            name="action dependency checking",
            ts=1_000_000,
            dur=100_000,
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.IGNORED

    def test_given_postprocessing_run_event_when_action_built_expect_ignored_type(self) -> None:
        event_str = make_event_str(
            cat=PECat.GENERAL_INFORMATION,
            name=PEName.ACTION_POSTPROCESSING,
            ts=1_000_000,
            dur=100_000,
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.IGNORED

    def test_given_fetching_repository_event_when_action_built_expect_ignored_type(self) -> None:
        event_str = make_event_str(
            cat=PECat.FETCHING_REPOSITORY, name="some_repo", ts=1_000_000, dur=100_000
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.IGNORED

    def test_given_unknown_cat_event_when_action_built_expect_unknown_type(self) -> None:
        event_str = make_event_str(
            cat=PECat.UNKNOWN, name="mystery event", ts=1_000_000, dur=100_000
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.action_type == ActionType.UNKNOWN


class TestExecutionActionMetrics:
    def test_given_execution_event_with_target_and_mnemonic_when_action_built_expect_metrics_populated(
        self,
    ) -> None:
        event_groups = [[make_execution_event()]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.metrics["target"] == "//my:lib"
        assert action.metrics["mnemonic"] == "CppCompile"

    def test_given_execution_event_with_duration_when_action_built_expect_total_duration_in_metrics(
        self,
    ) -> None:
        event_groups = [[make_execution_event(dur=5_000_000)]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.metrics["duration.total"] == "5000000"

    def test_given_execution_event_with_out_field_when_action_built_expect_out_in_metrics(
        self,
    ) -> None:
        event_groups = [[make_execution_event(out="bazel-out/k8-fastbuild/bin/my/lib.a")]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.metrics["out"] == "bazel-out/k8-fastbuild/bin/my/lib.a"

    def test_given_execution_event_without_out_field_when_action_built_expect_out_absent_from_metrics(
        self,
    ) -> None:
        event_groups = [[make_execution_event()]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert "out" not in action.metrics

    def test_given_execution_event_with_preceding_dependency_checking_when_action_built_expect_combined_total_duration(
        self,
    ) -> None:
        dep_event = make_dependency_checking_event(ts=500_000, dur=400_000)
        exec_event = make_execution_event(ts=1_000_000, dur=5_000_000)
        event_groups = [[dep_event], [exec_event]]
        action = Action(1, event_groups, BUILD_START_TIME)
        assert action.metrics["duration.total"] == str(5_000_000 + 400_000)

    def test_given_execution_event_with_preceding_dependency_checking_when_action_built_expect_dep_duration_in_metrics(
        self,
    ) -> None:
        dep_event = make_dependency_checking_event(ts=500_000, dur=400_000)
        exec_event = make_execution_event(ts=1_000_000, dur=5_000_000)
        event_groups = [[dep_event], [exec_event]]
        action = Action(1, event_groups, BUILD_START_TIME)
        assert "duration.action_dependency_checking" in action.metrics

    def test_given_execution_event_with_following_postprocessing_when_action_built_expect_combined_total_duration(
        self,
    ) -> None:
        exec_event = make_execution_event(ts=1_000_000, dur=5_000_000)
        post_event = make_postprocessing_event(ts=6_100_000, dur=200_000)
        event_groups = [[exec_event], [post_event]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.metrics["duration.total"] == str(5_000_000 + 200_000)

    def test_given_execution_event_with_child_events_when_action_built_expect_child_durations_in_metrics(
        self,
    ) -> None:
        exec_event = make_execution_event(ts=1_000_000, dur=5_000_000)
        child_event = make_event_str(
            cat=PECat.LOCAL_ACTION_EXECUTION,
            name="local action execution",
            ts=1_100_000,
            dur=4_000_000,
        )
        event_groups = [[exec_event, child_event]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert "duration.local_action_execution" in action.metrics


class TestRepoLoadingActionMetrics:
    def test_given_starlark_repo_event_with_external_name_when_action_built_expect_target_with_double_at(
        self,
    ) -> None:
        event_str = make_event_str(
            cat=PECat.STARLARK_REPOSITORY_FUNCTION_CALL,
            name="//external:my_repo",
            ts=1_000_000,
            dur=3_000_000,
        )
        event_groups = [[event_str]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.metrics["target"] == "@@my_repo"

    def test_given_starlark_repo_event_when_action_built_expect_total_duration_in_metrics(
        self,
    ) -> None:
        # The repo loading path stores primary_event["dur"] as-is (an int from json.loads),
        # unlike execution actions which explicitly call str() on the total.
        event_groups = [[make_repo_loading_event(dur=3_000_000)]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.metrics["duration.total"] == 3_000_000  # noqa: PLR2004

    def test_given_starlark_repo_event_with_builtin_child_when_action_built_expect_child_duration_in_metrics(
        self,
    ) -> None:
        repo_event = make_repo_loading_event(ts=1_000_000, dur=3_000_000)
        child_event = make_event_str(
            cat=PECat.STARLARK_BUILT_IN_FUNCTION_CALL,
            name="git_fetch",
            ts=1_100_000,
            dur=2_000_000,
        )
        event_groups = [[repo_event, child_event]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert "duration.git_fetch" in action.metrics

    def test_given_starlark_repo_event_with_non_builtin_child_when_action_built_expect_child_duration_absent_from_metrics(
        self,
    ) -> None:
        repo_event = make_repo_loading_event(ts=1_000_000, dur=3_000_000)
        child_event = make_event_str(
            cat=PECat.STARLARK_REPOSITORY_FUNCTION_CALL,
            name="some_nested_call",
            ts=1_100_000,
            dur=2_000_000,
        )
        event_groups = [[repo_event, child_event]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert "duration.some_nested_call" not in action.metrics


class TestActionTimestamp:
    def test_given_event_with_ts_zero_when_action_built_expect_timestamp_equals_build_start_time(
        self,
    ) -> None:
        event_groups = [[make_execution_event(ts=0)]]
        action = Action(0, event_groups, BUILD_START_TIME)
        assert action.metrics["timestamp"] == BUILD_START_TIME.isoformat()

    def test_given_event_with_nonzero_ts_when_action_built_expect_timestamp_offset_from_build_start(
        self,
    ) -> None:
        # ts is in microseconds; 1_000_000 µs = 1 second
        event_groups = [[make_execution_event(ts=1_000_000)]]
        action = Action(0, event_groups, BUILD_START_TIME)
        expected = (BUILD_START_TIME + datetime.timedelta(seconds=1)).isoformat()
        assert action.metrics["timestamp"] == expected
