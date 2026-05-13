"""An external repository for fetching build_event_stream protobufs.

Inspired by https://gist.github.com/fzakaria/9a1bdd5fff05cfd5c857f50a0322d98e
"""

load("@bazel_skylib//lib:paths.bzl", "paths")

_FILES = [
    "src/main/java/com/google/devtools/build/lib/buildeventstream/proto/build_event_stream.proto",
    "src/main/protobuf/command_line.proto",
    "src/main/protobuf/invocation_policy.proto",
    "src/main/protobuf/option_filters.proto",
    "src/main/java/com/google/devtools/build/lib/packages/metrics/package_load_metrics.proto",
    "src/main/protobuf/action_cache.proto",
    "src/main/protobuf/failure_details.proto",
    "src/main/protobuf/strategy_policy.proto",
]

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

def _bes_repo_rule(repository_ctx):
    attrs = {
        "name": repository_ctx.attr.name,
        "revision": repository_ctx.attr.revision,
        "sha256s": dict(repository_ctx.attr.sha256s),
    }
    proto_srcs = []
    for path in _FILES:
        url = _URL_TEMPLATE.format(
            revision = repository_ctx.attr.revision,
            path = path,
        )
        filename = paths.basename(path)
        proto_srcs.append("\"%s\"" % path)
        sha256 = repository_ctx.attr.sha256s.get(filename)
        if sha256:
            download_result = repository_ctx.download(
                url,
                output = path,
                canonical_id = url,
                sha256 = sha256,
            )
        else:
            download_result = repository_ctx.download(
                url,
                output = path,
                canonical_id = url,
            )
        attrs["sha256s"][filename] = download_result.sha256

    repository_ctx.file(
        "BUILD.bazel",
        _BUILD_FILE_TEMPLATE.format(
            filenames = ",\n        ".join(proto_srcs),
        ),
    )

bes_repo_rule = repository_rule(
    implementation = _bes_repo_rule,
    attrs = {
        "revision": attr.string(
            doc = "A tag, commit or branch string at which to fetch the required files.",
            default = "master",
        ),
        "sha256s": attr.string_dict(
            doc = "A mapping of basename to sha256 for the fetched files",
        ),
    },
)

def _build_event_service_repo(ctx):
    for mod in ctx.modules:
        for settings in mod.tags.settings:
            bes_repo_rule(
                name = settings.name,
                revision = settings.revision,
                sha256s = settings.sha256s,
            )

build_event_service_repo = module_extension(
    implementation = _build_event_service_repo,
    tag_classes = {
        "settings": tag_class(
            attrs = {
                "name": attr.string(
                    mandatory = True,
                    doc = "The name of the repository.",
                ),
                "revision": attr.string(
                    mandatory = True,
                    doc = "A tag, commit or branch string at which to fetch the required files.",
                ),
                "sha256s": attr.string_dict(
                    mandatory = True,
                    doc = "A mapping of basename to sha256 for the fetched files",
                ),
            },
        ),
    },
)
