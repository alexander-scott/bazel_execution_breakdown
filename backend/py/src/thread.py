import datetime
import logging
import time
from collections import defaultdict

from src.action import Action, ActionType
from src.profile_event_classifier import (
    PROFILE_CRITICAL_PATH_REGEX,
    PROFILE_DUR_REGEX,
    PROFILE_GC_REGEX,
    PROFILE_MAIN_THREAD_REGEX,
    PROFILE_RESOURCES_REGEX,
    PROFILE_TREE_DELETER,
    PROFILE_TS_REGEX,
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

    def _is_metadata_thread(self, events: list[str]) -> bool:
        """Return True if any event in the list is a metadata-thread marker."""
        for event in events:
            if (
                PROFILE_MAIN_THREAD_REGEX(event)
                or PROFILE_CRITICAL_PATH_REGEX(event)
                or PROFILE_RESOURCES_REGEX(event)
                or PROFILE_GC_REGEX(event)
                or PROFILE_TREE_DELETER(event)
            ):
                return True
        return False

    def _get_event_groups(self, thread_events: list[str]) -> list[list[str]]:
        if self._is_metadata_thread(thread_events):
            _logger.debug("Skipping thread because it's a metadata thread")
            return []

        event_groups: list[list[str]] = []

        current_event_group: list[str] = []
        current_group_end_time = None
        for event in sorted(thread_events, key=self._extract_timestamp):
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
            current_group_end_time = max(current_group_end_time, event_end_time)

        if current_event_group:
            event_groups.append(current_event_group)

        return event_groups

    def _build_actions_from_event_groups(
        self, event_groups: list[list[str]]
    ) -> dict[ActionType, list[Action]]:
        action_map: dict[ActionType, list[Action]] = defaultdict(list)
        unknown_actions: set[tuple[str | int, str | int]] = set()

        _logger.debug("Generating actions from event groups...")
        start_time = time.time()

        for index, _ in enumerate(event_groups):
            action = Action(index, event_groups, self.build_start_time)
            if action.action_type in [ActionType.EXECUTION, ActionType.REPOSITORY_LOADING]:
                action_map[action.action_type].append(action)
            elif action.action_type == ActionType.UNKNOWN:
                unknown_actions.add((action.metrics["cat"], action.metrics["name"]))

        end_time = time.time()
        _logger.debug(
            f"Built {len(action_map[ActionType.EXECUTION]) + len(action_map[ActionType.REPOSITORY_LOADING])} actions from {len(event_groups)} event groups in {end_time - start_time:.4f} seconds"
        )

        if len(unknown_actions) > 0:
            _logger.warning(
                f"[tid_{self.thread_id}] Skipped {len(unknown_actions)} event groups due to missing tracking:"
            )
            for action_name in unknown_actions:
                _logger.warning(f"  {action_name}")

        return action_map
