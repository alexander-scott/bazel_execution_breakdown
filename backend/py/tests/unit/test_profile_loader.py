import gzip
import tempfile
from pathlib import Path

import pytest
from src.profile_loader import read_profile_lines

SAMPLE_PROFILE_FIRST_LINE = (
    '{"otherData":{"build_id":"test-id","date":"2026-02-09T17:07:35.206537Z"},"traceEvents":[\n'
)
SAMPLE_PROFILE_EVENT = (
    '    {"cat":"action processing","name":"Test","ph":"X","ts":100,"dur":50,"pid":1,"tid":99},\n'
)


class TestReadProfileLinesWithGzipFile:
    def test_given_valid_gzip_profile_when_read_expect_lines_returned(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".profile.gz", delete=False) as tmp:
            content = (SAMPLE_PROFILE_FIRST_LINE + SAMPLE_PROFILE_EVENT).encode("utf-8")
            with gzip.open(tmp.name, "wb") as gz:
                gz.write(content)
            path = Path(tmp.name)

        lines = read_profile_lines(path)
        assert len(lines) == 2  # noqa: PLR2004

    def test_given_valid_gzip_profile_when_read_expect_first_line_contains_other_data(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".profile.gz", delete=False) as tmp:
            content = (SAMPLE_PROFILE_FIRST_LINE + SAMPLE_PROFILE_EVENT).encode("utf-8")
            with gzip.open(tmp.name, "wb") as gz:
                gz.write(content)
            path = Path(tmp.name)

        lines = read_profile_lines(path)
        assert "otherData" in lines[0]

    def test_given_valid_gzip_profile_when_read_expect_event_line_contains_action_cat(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".profile.gz", delete=False) as tmp:
            content = (SAMPLE_PROFILE_FIRST_LINE + SAMPLE_PROFILE_EVENT).encode("utf-8")
            with gzip.open(tmp.name, "wb") as gz:
                gz.write(content)
            path = Path(tmp.name)

        lines = read_profile_lines(path)
        assert "action processing" in lines[1]


class TestReadProfileLinesWithPlainTextFile:
    def test_given_valid_plain_text_profile_when_read_expect_lines_returned(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".profile", mode="w", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(SAMPLE_PROFILE_FIRST_LINE)
            tmp.write(SAMPLE_PROFILE_EVENT)
            path = Path(tmp.name)

        lines = read_profile_lines(path)
        assert len(lines) == 2  # noqa: PLR2004

    def test_given_valid_plain_text_profile_when_read_expect_event_line_present(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".profile", mode="w", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(SAMPLE_PROFILE_FIRST_LINE)
            tmp.write(SAMPLE_PROFILE_EVENT)
            path = Path(tmp.name)

        lines = read_profile_lines(path)
        assert any("action processing" in line for line in lines)


class TestReadProfileLinesErrorHandling:
    def test_given_nonexistent_file_when_read_expect_file_not_found_error(self) -> None:
        path = Path("/tmp/nonexistent_profile_xyz_abc.profile.gz")
        with pytest.raises(FileNotFoundError):
            read_profile_lines(path)

    def test_given_file_with_invalid_utf8_bytes_when_read_expect_value_error(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".profile", delete=False) as tmp:
            # Write raw bytes that are not valid UTF-8 and also not valid gzip
            tmp.write(b"\xff\xfe invalid utf-8 \x80\x81 content")
            path = Path(tmp.name)

        with pytest.raises(ValueError, match="not valid utf-8"):
            read_profile_lines(path)
