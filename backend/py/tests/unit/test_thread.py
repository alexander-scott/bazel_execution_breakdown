import datetime

from src.action import ActionType
from src.profile_event_classifier import PECat
from src.thread import Thread
from tests.conftest import make_raw_event

BUILD_START_TIME = datetime.datetime(2026, 2, 9, 17, 7, 35)


class TestExtractTimestamp:
    def test_given_event_with_valid_ts_when_timestamp_extracted_expect_float_value(self) -> None:
        thread = Thread.__new__(Thread)
        event = '    {"cat":"action processing","name":"Test","ts":7525816,"dur":1000,"pid":1,"tid":99},\n'
        assert thread._extract_timestamp(event) == 7525816.0  # pyright: ignore[reportPrivateUsage] # noqa: PLR2004

    def test_given_event_without_ts_when_timestamp_extracted_expect_zero(self) -> None:
        thread = Thread.__new__(Thread)
        event = '    {"cat":"action processing","name":"Test","dur":1000,"pid":1,"tid":99},\n'
        assert thread._extract_timestamp(event) == 0.0  # pyright: ignore[reportPrivateUsage]

    def test_given_event_with_ts_zero_when_timestamp_extracted_expect_zero(self) -> None:
        thread = Thread.__new__(Thread)
        event = '    {"name":"thread_name","ph":"M","pid":1,"tid":0,"ts":0},\n'
        assert thread._extract_timestamp(event) == 0.0  # pyright: ignore[reportPrivateUsage]


class TestGetEventGroups:
    def test_given_critical_path_first_event_when_groups_built_expect_empty_list(self) -> None:
        thread = Thread.__new__(Thread)
        events = [
            '    {"name":"Critical Path","ph":"M","pid":1,"tid":0,"ts":0,"dur":100},\n',
            make_raw_event(PECat.ACTION_PROCESSING, "SomeAction", ts=200, dur=100, tid=0),
        ]
        assert thread._get_event_groups(events) == []  # pyright: ignore[reportPrivateUsage]

    def test_given_main_thread_first_event_when_groups_built_expect_empty_list(self) -> None:
        thread = Thread.__new__(Thread)
        events = [
            '    {"name":"Main Thread","ph":"M","pid":1,"tid":34,"ts":0,"dur":100},\n',
        ]
        assert thread._get_event_groups(events) == []  # pyright: ignore[reportPrivateUsage]

    def test_given_collect_local_resources_first_event_when_groups_built_expect_empty_list(
        self,
    ) -> None:
        thread = Thread.__new__(Thread)
        events = [
            '    {"name":"collect-local-resources","ph":"M","pid":1,"tid":5,"ts":0,"dur":100},\n',
        ]
        assert thread._get_event_groups(events) == []  # pyright: ignore[reportPrivateUsage]

    def test_given_event_without_ts_when_groups_built_expect_event_skipped(self) -> None:
        thread = Thread.__new__(Thread)
        events = [
            '    {"cat":"action processing","name":"NoTimestamp","dur":1000,"pid":1,"tid":99},\n',
        ]
        assert thread._get_event_groups(events) == []  # pyright: ignore[reportPrivateUsage]

    def test_given_event_without_dur_when_groups_built_expect_event_skipped(self) -> None:
        thread = Thread.__new__(Thread)
        events = [
            '    {"cat":"action processing","name":"NoDuration","ts":1000,"pid":1,"tid":99},\n',
        ]
        assert thread._get_event_groups(events) == []  # pyright: ignore[reportPrivateUsage]

    def test_given_single_non_overlapping_event_when_groups_built_expect_one_group(self) -> None:
        thread = Thread.__new__(Thread)
        events = [make_raw_event(PECat.ACTION_PROCESSING, "Action1", ts=100, dur=50, tid=99)]
        groups = thread._get_event_groups(events)  # pyright: ignore[reportPrivateUsage]
        assert len(groups) == 1

    def test_given_two_non_overlapping_events_when_groups_built_expect_two_groups(self) -> None:
        thread = Thread.__new__(Thread)
        # Event A: ts=100, dur=50 → ends at 150. Event B: ts=200 → starts after A ends.
        events = [
            make_raw_event(PECat.ACTION_PROCESSING, "Action1", ts=100, dur=50, tid=99),
            make_raw_event(PECat.ACTION_PROCESSING, "Action2", ts=200, dur=50, tid=99),
        ]
        groups = thread._get_event_groups(events)  # pyright: ignore[reportPrivateUsage]
        assert len(groups) == 2  # noqa: PLR2004

    def test_given_two_overlapping_events_when_groups_built_expect_one_group(self) -> None:
        thread = Thread.__new__(Thread)
        # Event A: ts=100, dur=200 → ends at 300. Event B: ts=150 → starts within A.
        events = [
            make_raw_event(PECat.ACTION_PROCESSING, "Parent", ts=100, dur=200, tid=99),
            make_raw_event(PECat.LOCAL_ACTION_EXECUTION, "Child", ts=150, dur=50, tid=99),
        ]
        groups = thread._get_event_groups(events)  # pyright: ignore[reportPrivateUsage]
        assert len(groups) == 1
        assert len(groups[0]) == 2  # noqa: PLR2004

    def test_given_overlapping_events_when_groups_built_expect_events_cleaned_of_trailing_comma(
        self,
    ) -> None:
        thread = Thread.__new__(Thread)
        events = [
            make_raw_event(PECat.ACTION_PROCESSING, "Parent", ts=100, dur=200, tid=99),
            make_raw_event(PECat.LOCAL_ACTION_EXECUTION, "Child", ts=150, dur=50, tid=99),
        ]
        groups = thread._get_event_groups(events)  # pyright: ignore[reportPrivateUsage]
        for event_str in groups[0]:
            assert not event_str.endswith(",")
            assert not event_str.endswith("\n")

    def test_given_three_events_with_one_overlap_when_groups_built_expect_two_groups(self) -> None:
        thread = Thread.__new__(Thread)
        # Group 1: ts=100 dur=200 (ends 300), ts=150 dur=50 (ends 200) → overlap
        # Group 2: ts=400 dur=100 → separate
        events = [
            make_raw_event(PECat.ACTION_PROCESSING, "Parent", ts=100, dur=200, tid=99),
            make_raw_event(PECat.LOCAL_ACTION_EXECUTION, "Child", ts=150, dur=50, tid=99),
            make_raw_event(PECat.ACTION_PROCESSING, "Separate", ts=400, dur=100, tid=99),
        ]
        groups = thread._get_event_groups(events)  # pyright: ignore[reportPrivateUsage]
        assert len(groups) == 2  # noqa: PLR2004
        assert len(groups[0]) == 2  # noqa: PLR2004
        assert len(groups[1]) == 1


class TestThreadActionBuilding:
    def test_given_execution_events_when_thread_built_expect_execution_actions_present(
        self,
    ) -> None:
        events = [
            make_raw_event(
                PECat.ACTION_PROCESSING,
                "CppCompile test.cpp",
                ts=100,
                dur=500,
                tid=99,
                args={"target": "//test:foo", "mnemonic": "CppCompile"},
            )
        ]
        thread = Thread("99", events, BUILD_START_TIME)
        assert len(thread.actions[ActionType.EXECUTION]) == 1

    def test_given_repo_loading_events_when_thread_built_expect_repository_loading_actions_present(
        self,
    ) -> None:
        events = [
            make_raw_event(
                PECat.STARLARK_REPOSITORY_FUNCTION_CALL,
                "//external:some_dep",
                ts=100,
                dur=500,
                tid=99,
            )
        ]
        thread = Thread("99", events, BUILD_START_TIME)
        assert len(thread.actions[ActionType.REPOSITORY_LOADING]) == 1

    def test_given_ignored_events_when_thread_built_expect_no_execution_or_repo_actions(
        self,
    ) -> None:
        events = [
            make_raw_event(PECat.PACKAGE_CREATION, "some/package", ts=100, dur=50, tid=99),
        ]
        thread = Thread("99", events, BUILD_START_TIME)
        assert len(thread.actions.get(ActionType.EXECUTION, [])) == 0
        assert len(thread.actions.get(ActionType.REPOSITORY_LOADING, [])) == 0

    def test_given_metadata_thread_events_when_thread_built_expect_no_actions(self) -> None:
        events = [
            '    {"name":"Critical Path","ph":"M","pid":1,"tid":0,"ts":0,"dur":100},\n',
        ]
        thread = Thread("0", events, BUILD_START_TIME)
        assert len(thread.actions.get(ActionType.EXECUTION, [])) == 0
        assert len(thread.actions.get(ActionType.REPOSITORY_LOADING, [])) == 0

    def test_given_mixed_events_when_thread_built_expect_only_relevant_actions_counted(
        self,
    ) -> None:
        events = [
            make_raw_event(
                PECat.ACTION_PROCESSING,
                "JavaCompile Main.java",
                ts=100,
                dur=300,
                tid=99,
                args={"target": "//main:app", "mnemonic": "JavaCompile"},
            ),
            make_raw_event(PECat.PACKAGE_CREATION, "ignored/package", ts=500, dur=10, tid=99),
            make_raw_event(
                PECat.STARLARK_REPOSITORY_FUNCTION_CALL,
                "//external:dep",
                ts=600,
                dur=200,
                tid=99,
            ),
        ]
        thread = Thread("99", events, BUILD_START_TIME)
        assert len(thread.actions[ActionType.EXECUTION]) == 1
        assert len(thread.actions[ActionType.REPOSITORY_LOADING]) == 1
