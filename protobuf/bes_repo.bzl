"""An external repository for fetching build_event_stream protobufs.

Inspired by https://gist.github.com/fzakaria/9a1bdd5fff05cfd5c857f50a0322d98e
"""

_URL_TEMPLATE = "https://raw.githubusercontent.com/bazelbuild/bazel/{revision}/{path}"

_BUILD_FILE_TEMPLATE = """
load("@rules_proto//proto:defs.bzl", "proto_library")

proto_library(
    name = "build_event_stream_proto",
    deps = [
        "@com_google_protobuf//:any_proto",
        "@com_google_protobuf//:duration_proto",
        "@com_google_protobuf//:timestamp_proto",
        "@com_google_protobuf//:descriptor_proto",
    ],
    srcs = [
        {filenames},
    ],
    visibility = ["//visibility:public"],
)
"""

def _get_revision(repository_ctx) -> str:
    """
    Extracts the current bazel version from the .bazelversion file at the root of the repo.
    """

    bazelversion_path = repository_ctx.workspace_root.get_child(".bazelversion")
    version = repository_ctx.read(bazelversion_path).strip()
    return version

def _bes_repo_rule(repository_ctx):
    bazel_version = _get_revision(repository_ctx)

    proto_srcs = []
    for path, sha256 in repository_ctx.attr.files.items():
        url = _URL_TEMPLATE.format(
            revision = bazel_version,
            path = path,
        )
        proto_srcs.append("\"%s\"" % path)
        repository_ctx.download(
            url,
            output = path,
            canonical_id = url,
            sha256 = sha256,
        )

    repository_ctx.file(
        "BUILD.bazel",
        _BUILD_FILE_TEMPLATE.format(
            filenames = ",\n        ".join(proto_srcs),
        ),
    )

bes_repo_rule = repository_rule(
    implementation = _bes_repo_rule,
    attrs = {
        "files": attr.string_dict(
            doc = "A mapping of filepath to sha256 for the fetched files",
        ),
    },
)

def _build_event_service_repo(ctx):
    for mod in ctx.modules:
        for settings in mod.tags.settings:
            bes_repo_rule(
                name = settings.name,
                files = settings.files,
            )

build_event_service_repo = module_extension(
    implementation = _build_event_service_repo,
    tag_classes = {
        "settings": tag_class(
            attrs = {
                "files": attr.string_dict(
                    mandatory = True,
                    doc = "A mapping of filepath to sha256 for the fetched files",
                ),
                "name": attr.string(
                    mandatory = True,
                    doc = "The name of the repository.",
                ),
            },
        ),
    },
)
