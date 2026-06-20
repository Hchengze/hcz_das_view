from das_view.core.data_model import DASMetadata
from das_view.core.metadata_format import (
    format_metadata,
    metadata_summary_lines,
    metadata_to_dict,
)


def test_metadata_to_dict_and_duration_are_stable():
    metadata = DASMetadata(
        n_samples=100,
        n_channels=5,
        sample_rate_hz=50.0,
        dx_m=2.0,
        gauge_length_m=10.0,
        start_channel=3,
        start_time="synthetic",
        source_format="test",
        source_path="sample.h5",
    )

    values = metadata_to_dict(metadata)

    assert values["source_format"] == "test"
    assert values["n_samples"] == 100
    assert values["n_channels"] == 5
    assert values["duration_s"] == 2.0
    assert values["distance_range_m"] == (0.0, 8.0)


def test_metadata_format_displays_missing_values_as_na():
    metadata = DASMetadata(n_samples=10, n_channels=2)

    text = format_metadata(metadata)
    lines = metadata_summary_lines(metadata)

    assert "source_format: N/A" in text
    assert "sample_rate_hz: N/A" in text
    assert "duration_s: N/A" in text
    assert "channel_range: (0, 1)" in lines
