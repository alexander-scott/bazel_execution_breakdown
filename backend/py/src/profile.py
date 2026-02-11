import datetime
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

from src.action import Action
from src.profile_event_classifier import PROFILE_TID_REGEX
from src.profile_loader import read_profile_lines
from src.thread import Thread

_logger = logging.getLogger()


class Profile:
    def __init__(self, file: Path) -> None:
        _events: list[str] = read_profile_lines(file)

        self.build_id, self.build_start_time = self._extract_profile_metadata(_events)
        """
        Metadata found within the first line of the bazel profile
        """

        self.threads: list[Thread] = self._organise_events_into_threads(_events)
        """
        A list of threads found within the profile. Each thread contains a list of actions.
        """

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        for thread in self.threads:
            for thread_actions in thread.actions.values():
                actions.extend(thread_actions)
        return actions

    def _extract_profile_metadata(self, profile_data: list[str]) -> tuple[str, datetime.datetime]:
        # The first line of the profile data contains metadata about the profile.
        # We just need to close the list and then load it as JSON and extract the data.
        profile_metadata = json.loads(f"{profile_data[0]}]}}")
        build_id = profile_metadata.get("otherData").get("build_id")
        # Note: %fZ is not correctly detected in < Python 3.11 so we'll remove the last 4 chars
        build_start_time = datetime.datetime.strptime(
            profile_metadata.get("otherData").get("date")[:-4], "%Y-%m-%dT%H:%M:%S.%f"
        )
        return build_id, build_start_time

    def _organise_events_into_threads(self, events: list[str]) -> list[Thread]:
        thread_map: dict[str, list[str]] = defaultdict(list)

        _logger.info("Sorting events into threads...")
        start_time = time.time()

        for event in events:
            match = PROFILE_TID_REGEX(event)
            if match is not None:
                thread_map[match.group(1)].append(event)

        threads: list[Thread] = []
        for thread_id, thread_events in thread_map.items():
            threads.append(Thread(thread_id, thread_events, self.build_start_time))

        end_time = time.time()
        _logger.info(
            f"Processed {len(events)} events into {len(thread_map)} threads in {end_time - start_time:.4f} seconds"
        )

        return threads
