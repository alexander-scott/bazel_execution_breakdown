import logging
import pkgutil
import sys
from concurrent import futures

# build_event_stream_pb2 uses src.main.* import paths, but backend/py/ is also
# on sys.path with its own src/ package that shadows them. Move the BES stubs
# directory to the front so src.main.* resolves correctly.
_bes_pb_path = next((p for p in sys.path if "build_event_stream_grpc_pb" in p), None)
if _bes_pb_path:
    sys.path.remove(_bes_pb_path)
    sys.path.insert(0, _bes_pb_path)

import google

google.__path__ = pkgutil.extend_path(google.__path__, google.__name__)

import google.devtools

google.devtools.__path__ = pkgutil.extend_path(google.devtools.__path__, google.devtools.__name__)

import google.devtools.build

google.devtools.build.__path__ = pkgutil.extend_path(
    google.devtools.build.__path__, google.devtools.build.__name__
)

import google.devtools.build.v1

google.devtools.build.v1.__path__ = pkgutil.extend_path(
    google.devtools.build.v1.__path__, google.devtools.build.v1.__name__
)

import grpc
from google.devtools.build.v1 import publish_build_event_pb2, publish_build_event_pb2_grpc
from google.protobuf import empty_pb2
from src.main.java.com.google.devtools.build.lib.buildeventstream.proto import (
    build_event_stream_pb2,
)


class BuildEventServicer(publish_build_event_pb2_grpc.PublishBuildEventServicer):
    def PublishLifecycleEvent(self, request, context):
        return empty_pb2.Empty()

    def PublishBuildToolEventStream(self, request_iterator, context):
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


def serve():
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
