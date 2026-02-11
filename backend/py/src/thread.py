import datetime
import json
import logging
import time
from collections import defaultdict

from src.action import Action, ExecutionAction, RepositoryLoadingAction
from src.action_filter import ActionType
from src.profile_event_classifier import (
    PROFILE_CRITICAL_PATH_REGEX,
    PROFILE_DUR_REGEX,
    PROFILE_GC_REGEX,
    PROFILE_MAIN_THREAD_REGEX,
    PROFILE_RESOURCES_REGEX,
    PROFILE_TS_REGEX,
    ProfileEventTypeClassifier,
)

_logger = logging.getLogger()


class Thread:
    def __init__(
        self, thread_id: str, events: list[str], build_start_time: datetime.datetime
    ) -> None:
        self.thread_id: str = thread_id
        self.build_start_time: datetime.datetime = build_start_time

        self.actions: dict[ActionType, list[Action]] = self._build_actions_from_event_groups(
            self._get_event_groups(events)
        )

    def _extract_timestamp(self, event: str) -> float:
        match = PROFILE_TS_REGEX(event)
        return float(match.group(1)) if match else 0

    def _get_event_groups(self, thread_events: list[str]) -> list[list[str]]:
        event_groups: list[list[str]] = []

        current_event_group: list[str] = []
        current_group_end_time = None
        for index, event in enumerate(sorted(thread_events, key=self._extract_timestamp)):
            if index == 0 and (
                PROFILE_MAIN_THREAD_REGEX(event)
                or PROFILE_CRITICAL_PATH_REGEX(event)
                or PROFILE_RESOURCES_REGEX(event)
                or PROFILE_GC_REGEX(event)
            ):
                _logger.debug(f"Skipping thread because it's a metadata thread: {event}")
                return []

            ts = PROFILE_TS_REGEX(event)
            dur = PROFILE_DUR_REGEX(event)
            if not (ts and dur):
                _logger.debug(f"Skipping event because timestamp or duration is missing: {event}")
                continue

            event_start_time = float(ts.group(1))
            event_end_time = event_start_time + (float(dur.group(1)))
            if current_group_end_time is None or (event_start_time > current_group_end_time):
                if current_event_group:
                    event_groups.append(current_event_group)
                current_group_end_time = event_end_time
                current_event_group = []

            current_event_group.append(event.replace(",\n", "").strip())

        if current_event_group:
            event_groups.append(current_event_group)

        return event_groups

    def _build_actions_from_event_groups(
        self, event_groups: list[list[str]]
    ) -> dict[ActionType, list[Action]]:
        action_map: dict[ActionType, list[Action]] = defaultdict(list)
        untracked_event_groups: dict[tuple[str, str], int] = defaultdict(int)

        _logger.debug("Generating actions from event groups...")
        start_time = time.time()

        for index, event_group in enumerate(event_groups):
            primary_event: dict[str, str] = json.loads(event_group[0])

            ### Core event types that we are interested in ###
            if ProfileEventTypeClassifier.is_action_processing_event(primary_event):
                action_map[ActionType.EXECUTION].append(
                    ExecutionAction(primary_event, index, event_groups, self.build_start_time)
                )
            elif ProfileEventTypeClassifier.is_starlark_repository_function_call_event(
                primary_event
            ):
                action_map[ActionType.REPOSITORY_LOADING].append(
                    RepositoryLoadingAction(
                        primary_event, index, event_groups, self.build_start_time
                    )
                )

            ### Event types that we are explicitly not interested in ##
            elif (
                # These events are mostly file read operations and are so negligible (under 1ms)
                # that it's definitely not worth tracking them.
                ProfileEventTypeClassifier.is_package_creation_event(primary_event)
                or ProfileEventTypeClassifier.is_check_outputs_event(primary_event)
                or ProfileEventTypeClassifier.is_discover_inputs_event(primary_event)
                ###
                # These events are always associated with an action processing event
                # and are already being tracked in the `_process_execution_event_group` function.
                or ProfileEventTypeClassifier.is_action_dependency_checking_event(primary_event)
                or ProfileEventTypeClassifier.is_action_post_processing_run_event(primary_event)
                ###
                # A fetching repository event by itself is essentially an event that checks that
                # the bazel external repository is up to date. If the repository is up to date, e.g.
                # it's in the cache, then this event is negligible. If the repository is not up to date,
                # then the event is associated with a starlark repository function call event and
                # is already being tracked in the `_process_repository_loading_event_group` function.
                or ProfileEventTypeClassifier.is_fetching_repository_event(primary_event)
            ):
                continue

            ### Event types that we do not have any tracking logic for ###
            else:
                untracked_event_groups[(primary_event["cat"], primary_event["name"])] += 1

        end_time = time.time()
        _logger.debug(
            f"Built {len(action_map[ActionType.EXECUTION]) + len(action_map[ActionType.REPOSITORY_LOADING])} actions from {len(event_groups)} event groups in {end_time - start_time:.4f} seconds"
        )

        if len(untracked_event_groups) > 0:
            _logger.warning(
                f"[tid_{self.thread_id}] Skipped {len(untracked_event_groups)} event groups due to missing tracking:"
            )
            for group, count in untracked_event_groups.items():
                _logger.warning(f"  {group[0]}: {group[1]}: {count} events")

        return action_map
