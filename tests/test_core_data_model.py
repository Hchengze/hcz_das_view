import numpy as np
import pytest

from das_view.core.data_model import DASData, DASMetadata
from das_view.core.exceptions import DataDimensionError


def test_metadata_initializes_dt_from_sample_rate():
    metadata = DASMetadata(n_samples=4, n_channels=3, sample_rate_hz=100.0)

    assert metadata.n_samples == 4
    assert metadata.n_channels == 3
    assert metadata.dt_s == pytest.approx(0.01)


def test_das_data_accepts_internal_dimension_convention():
    metadata = DASMetadata(n_samples=4, n_channels=3, sample_rate_hz=100.0)
    data = np.zeros((4, 3))

    das_data = DASData(data=data, metadata=metadata)

    assert das_data.data.shape == (4, 3)
    assert das_data.n_samples == 4
    assert das_data.n_channels == 3


def test_das_data_rejects_shape_that_does_not_match_metadata():
    metadata = DASMetadata(n_samples=4, n_channels=3)

    with pytest.raises(DataDimensionError):
        DASData(data=np.zeros((3, 4)), metadata=metadata)


def test_das_data_rejects_non_2d_array():
    metadata = DASMetadata(n_samples=4, n_channels=3)

    with pytest.raises(DataDimensionError):
        DASData(data=np.zeros((4, 3, 1)), metadata=metadata)
