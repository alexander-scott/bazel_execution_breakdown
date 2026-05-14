import importlib
import logging
import pkgutil
import sys
from collections.abc import Iterator
from concurrent import futures

import grpc

# build_event_stream_pb2 uses src.main.* import paths, but backend/py/ is also
# on sys.path with its own src/ package that shadows them. Move the BES stubs
# directory to the front so src.main.* resolves correctly.
_bes_pb_path = next((p for p in sys.path if "build_event_stream_grpc_pb" in p), None)
if _bes_pb_path:
    sys.path.remove(_bes_pb_path)
    sys.path.insert(0, _bes_pb_path)

# The google.devtools.build.v1 namespace is split across multiple runfile
# directories; extend each level so all fragments are visible.
for _ns in ("google", "google.devtools", "google.devtools.build", "google.devtools.build.v1"):
    _mod = importlib.import_module(_ns)
    _mod.__path__ = pkgutil.extend_path(_mod.__path__, _mod.__name__)

from google.devtools.build.v1 import (  # noqa: E402
    publish_build_event_pb2,
    publish_build_event_pb2_grpc,
)
from google.protobuf import empty_pb2  # noqa: E402
from src.main.java.com.google.devtools.build.lib.buildeventstream.proto import (  # noqa: E402
    build_event_stream_pb2,
)


class BuildEventServicer(publish_build_event_pb2_grpc.PublishBuildEventServicer):  # type: ignore
    def PublishLifecycleEvent(  # noqa: N802
        self,
        request: publish_build_event_pb2.PublishLifecycleEventRequest,
        context: grpc.ServicerContext,
    ) -> empty_pb2.Empty:
        return empty_pb2.Empty()

    def PublishBuildToolEventStream(  # noqa: N802
        self,
        request_iterator: Iterator[publish_build_event_pb2.PublishBuildToolEventStreamRequest],
        context: grpc.ServicerContext,
    ) -> Iterator[publish_build_event_pb2.PublishBuildToolEventStreamResponse]:
        for request in request_iterator:
            ordered_event = request.ordered_build_event
            if ordered_event.event.HasField("bazel_event"):
                bes_event = build_event_stream_pb2.BuildEvent()
                ordered_event.event.bazel_event.Unpack(bes_event)
                # process bes_event here...

            yield publish_build_event_pb2.PublishBuildToolEventStreamResponse(
                stream_id=ordered_event.stream_id,
                sequence_number=ordered_event.sequence_number,
            )


def serve() -> None:
    port = "50051"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    publish_build_event_pb2_grpc.add_PublishBuildEventServicer_to_server(
        BuildEventServicer(), server
    )
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started, listening on " + port)
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
