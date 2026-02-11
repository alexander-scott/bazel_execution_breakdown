# Bazel Execution Breakdown

> [!WARNING]
> This is still work in progress and more of a fun side-project for me.

If you have tens of thousands of Bazel builds per day, would you want to know:

- Where your bazel builds spend most of their time?
- Which actions are frequently uncached/invalidated?
- Which cache an action was retrieved from (remote cache, disk cache, execroot) and how long it took?
- Which actions were executed with which strategy?
- Which external repositories need to be re-downloaded the most often?

Then this tool can help you out. It consists of two components: the frontend and the backend/database. The backend will analyse your bazel profile and build event protocols and store it in a database, and the frontend will render that data for you with various filter/breakdown options.

## Generating a bazel profile

```bash
$ bazel build --profile=profile.gz --noslim_profile --experimental_profile_include_target_label --experimental_profile_include_primary_output //...
```

## Getting started

### Pre-requisites

First, ensure you have [UV](https://docs.astral.sh/uv/getting-started/installation/) installed on your local machine. Then, set up a virtual environment and install the dependencies from `pyproject.toml` file with:

```bash
uv sync
source .venv/bin/activate
```

You can also run the pre-commit linters with:

```bash
uv tool run -- prek run --all-files
```

> [!NOTE]
> [prek](https://github.com/j178/prek) is the rust based version of pre-commit.
