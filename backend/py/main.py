import logging
from pathlib import Path

import typer
from src.action_filter import ActionFilterType
from src.profile import Profile

app = typer.Typer()

_logger = logging.getLogger()


@app.command()
def main(input_bazel_profile_path: Path, action_filter: ActionFilterType) -> None:
    profile = Profile(input_bazel_profile_path)
    actions = profile.get_actions(action_filter)
    _logger.info(
        f"Build_ID: {profile.build_id}. Timestamp: {profile.build_start_time}. Total actions: {len(actions)}"
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, "INFO"),
        format="[%(levelname)s] [%(created)f]: %(message)s",
    )
    app()
