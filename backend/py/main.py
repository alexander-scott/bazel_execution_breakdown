import logging
from pathlib import Path

import typer
from src.action_filter import ActionFilterType, filter_actions
from src.profile import Profile

app = typer.Typer()


@app.command()
def main(input_bazel_profile_path: Path, action_filter: ActionFilterType) -> None:
    profile = Profile(input_bazel_profile_path)
    filtered_execution_actions = filter_actions(profile.get_actions(), action_filter)
    print(f"Build_ID: {profile.build_id}. Total actions: {len(filtered_execution_actions)}")


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, "INFO"),
        format="[%(levelname)s] [%(created)f]: %(message)s",
    )
    app()
