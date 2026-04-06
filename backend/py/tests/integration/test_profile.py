from pathlib import Path

import pytest
from src.action import Action, ActionType
from src.action_filter import ActionFilterType
from src.profile import Profile


@pytest.fixture
def plain_profile_path(profiles_dir: Path) -> Path:
    return profiles_dir / "clean-build-noslim.profile"


@pytest.fixture
def gzip_profile_path(profiles_dir: Path) -> Path:
    return profiles_dir / "clean-build-noslim.profile.gz"


@pytest.fixture
def single_action_profile_path(profiles_dir: Path) -> Path:
    return profiles_dir / "single-action-noslim.profile.gz"


@pytest.fixture
def loaded_profile(plain_profile_path: Path) -> Profile:
    return Profile(plain_profile_path)


class TestProfileLoading:
    def test_given_plain_text_profile_file_when_profile_loaded_expect_build_id_present(
        self, loaded_profile: Profile
    ) -> None:
        assert loaded_profile.build_id is not None
        assert len(loaded_profile.build_id) > 0

    def test_given_plain_text_profile_file_when_profile_loaded_expect_build_start_time_present(
        self, loaded_profile: Profile
    ) -> None:
        assert loaded_profile.build_start_time is not None

    def test_given_plain_text_profile_file_when_profile_loaded_expect_build_id_is_known_uuid(
        self, plain_profile_path: Path
    ) -> None:
        profile = Profile(plain_profile_path)
        assert profile.build_id == "ed0d909f-1943-4d5b-986a-d36f3baf7318"

    def test_given_gzip_profile_file_when_profile_loaded_expect_same_build_id_as_plain(
        self, plain_profile_path: Path, gzip_profile_path: Path
    ) -> None:
        plain = Profile(plain_profile_path)
        gzipped = Profile(gzip_profile_path)
        assert plain.build_id == gzipped.build_id

    def test_given_plain_text_profile_file_when_profile_loaded_expect_threads_present(
        self, loaded_profile: Profile
    ) -> None:
        assert len(loaded_profile.threads) > 0

    def test_given_nonexistent_profile_file_when_profile_loaded_expect_file_not_found_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            Profile(tmp_path / "does_not_exist.profile")


class TestGetActionsWithAllFilter:
    def test_given_loaded_profile_when_get_actions_with_all_filter_expect_actions_returned(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        assert len(actions) > 0

    def test_given_loaded_profile_when_get_actions_with_all_filter_expect_action_instances_returned(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        assert all(isinstance(a, Action) for a in actions)

    def test_given_loaded_profile_when_get_actions_with_all_filter_expect_only_execution_and_repo_types(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        valid_types = {ActionType.EXECUTION, ActionType.REPOSITORY_LOADING}
        assert all(a.action_type in valid_types for a in actions)


class TestGetActionsWithExecutedFilter:
    def test_given_loaded_profile_when_get_actions_with_executed_filter_expect_actions_returned(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.EXECUTED)
        assert len(actions) > 0

    def test_given_loaded_profile_when_get_actions_with_executed_filter_expect_each_action_has_execution_duration(
        self, loaded_profile: Profile
    ) -> None:
        execution_duration_fields = {
            "duration.execute_remotely",
            "duration.subprocess.run",
            "duration.local_action_execution",
        }
        actions = loaded_profile.get_actions(ActionFilterType.EXECUTED)
        for action in actions:
            assert any(field in action.metrics for field in execution_duration_fields)

    def test_given_loaded_profile_when_executed_filter_applied_expect_fewer_actions_than_all_filter(
        self, loaded_profile: Profile
    ) -> None:
        all_actions = loaded_profile.get_actions(ActionFilterType.ALL)
        executed_actions = loaded_profile.get_actions(ActionFilterType.EXECUTED)
        assert len(executed_actions) <= len(all_actions)


class TestGetActionsWithRemoteFilter:
    def test_given_loaded_profile_when_get_actions_with_executed_remotely_filter_expect_subset_of_executed(
        self, loaded_profile: Profile
    ) -> None:
        executed = loaded_profile.get_actions(ActionFilterType.EXECUTED)
        remote = loaded_profile.get_actions(ActionFilterType.EXECUTED_REMOTELY)
        assert len(remote) <= len(executed)

    def test_given_loaded_profile_when_get_actions_with_executed_remotely_filter_expect_each_action_has_remote_duration(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.EXECUTED_REMOTELY)
        for action in actions:
            assert "duration.execute_remotely" in action.metrics


class TestGetActionsWithLocalFilter:
    def test_given_loaded_profile_when_get_actions_with_executed_locally_filter_expect_each_action_has_local_duration(
        self, loaded_profile: Profile
    ) -> None:
        local_duration_fields = {"duration.subprocess.run", "duration.local_action_execution"}
        actions = loaded_profile.get_actions(ActionFilterType.EXECUTED_LOCALLY)
        for action in actions:
            assert any(field in action.metrics for field in local_duration_fields)

    def test_given_loaded_profile_when_executed_locally_filter_applied_expect_no_remote_only_actions(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.EXECUTED_LOCALLY)
        local_fields = {"duration.subprocess.run", "duration.local_action_execution"}
        for action in actions:
            assert any(field in action.metrics for field in local_fields)


class TestActionMetricsIntegrity:
    def test_given_loaded_profile_when_actions_retrieved_expect_all_actions_have_name_metric(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        assert all("name" in a.metrics for a in actions)

    def test_given_loaded_profile_when_actions_retrieved_expect_all_actions_have_cat_metric(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        assert all("cat" in a.metrics for a in actions)

    def test_given_loaded_profile_when_actions_retrieved_expect_all_actions_have_timestamp_metric(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        assert all("timestamp" in a.metrics for a in actions)

    def test_given_loaded_profile_when_execution_actions_retrieved_expect_all_have_total_duration(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        execution_actions = [a for a in actions if a.action_type == ActionType.EXECUTION]
        assert all("duration.total" in a.metrics for a in execution_actions)

    def test_given_loaded_profile_when_execution_actions_retrieved_expect_all_have_mnemonic(
        self, loaded_profile: Profile
    ) -> None:
        actions = loaded_profile.get_actions(ActionFilterType.ALL)
        execution_actions = [a for a in actions if a.action_type == ActionType.EXECUTION]
        assert all("mnemonic" in a.metrics for a in execution_actions)

    def test_given_single_action_profile_when_loaded_expect_at_least_one_execution_action(
        self, single_action_profile_path: Path
    ) -> None:
        profile = Profile(single_action_profile_path)
        execution_actions = [
            a
            for thread in profile.threads
            for actions in thread.actions.values()
            for a in actions
            if a.action_type == ActionType.EXECUTION
        ]
        assert len(execution_actions) >= 1
