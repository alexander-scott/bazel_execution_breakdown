import gzip
import logging
import time
from pathlib import Path

_logger = logging.getLogger()


def read_profile_lines(path_to_profile: Path) -> list[str]:
    """
    Processes a profile file and returns its content as a list.

    This function attempts to read the content of a profile file, which may be
    compressed using gzip. If the gzip reading fails for any reason, it falls
    back to reading the file as a regular text file. Any exceptions encountered
    during the file reading process are logged.

    Args:
        path_to_profile (Path): The path to the profile file to be processed.

    Returns:
        list[str]: A list containing the lines of the profile file. If an
        exception occurs, an exception is raised.
    """
    _logger.info(f"Reading profile {path_to_profile}...")
    if not path_to_profile.exists():
        raise FileNotFoundError(f"Profile file does not exist: {path_to_profile}")

    data = []
    start_time = time.time()
    try:
        try:
            with gzip.open(path_to_profile, "rt", encoding="utf-8") as file:
                data = file.readlines()
        except Exception:
            try:
                with open(path_to_profile, encoding="utf-8") as file:
                    data = file.readlines()
            except UnicodeDecodeError as ex:
                raise ValueError(f"Profile file is not valid utf-8 {path_to_profile}") from ex
    except Exception:
        _logger.exception("Exception caught when trying to open profile %s", path_to_profile)
        raise

    end_time = time.time()
    _logger.debug(f"Time taken to read profile: {end_time - start_time:.4f} seconds")

    return data
