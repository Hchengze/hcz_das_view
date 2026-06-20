# Data Formats

## Internal convention

All data exposed by readers must use:

    data.shape == (n_samples, n_channels)

Reader implementations must transpose or reshape source data when required.

## ZD HDF5

Old-code source: old_code/old_code1/tools/data_tools.py.

Known raw dataset path:

    /Acquisition/Raw[0]/RawData

Known metadata locations and names:

- /Acquisition/Raw[0]
  - NumberOfLoci
  - OutputDataRate
- /Acquisition
  - SpatialSamplingInterval
  - GaugeLength
- /Acquisition/Raw[0]/RawDataTime
  - Count
  - EndTime
  - PartEndTime
- /Acquisition/Raw[0]/RawData
  - PartStartTime
  - PartEndTime

Current reader support:

- can_read(path) checks .h5/.hdf5 extension and, when the file exists and h5py can open it, verifies that the ZD raw dataset exists.
- read_metadata(path) reads shape and attributes without loading the raw data array.
- read(path, time_slice=None, channel_slice=None, downsample=None) supports slicing and simple stride downsampling.
- downsample may be an int or (time_step, channel_step).
- metadata.extra_attrs records raw_shape, raw_orientation, orientation_basis, and key HDF5 paths.

Orientation logic:

- If raw_shape == (Count, NumberOfLoci), raw orientation is time_channel.
- If raw_shape == (NumberOfLoci, Count), raw orientation is channel_time and the reader transposes to internal convention.
- If only one hint exists, it must match exactly one axis.
- If orientation is ambiguous or cannot be inferred from Count/NumberOfLoci, the reader raises ReaderError instead of guessing.

Slicing and downsampling:

- Slices are specified in internal coordinates: time first, channel second.
- For channel_time raw data, the reader maps internal slices to raw HDF5 axes and transposes the result.
- Sliced metadata updates n_samples, n_channels, sample_rate_hz, dt_s, dx_m, start_channel, and extra_attrs.

## Puniu DAT

Old-code source: old_code/old_code3/dy_view.py::read_puniu_dat_file.

Known layout:

- Header: first 10 float64 values, 80 bytes total.
- Data: float32 values after the seek offset.

Header fields:

| Index | Meaning |
|---:|---|
| 0 | channel count |
| 1 | dx / channel spacing related value |
| 2 | npts / sample count |
| 3 | dt in seconds |
| 4 | data format code |
| 5 | timestamp seconds |
| 6 | timestamp nanoseconds |
| 7 | start channel |
| 8 | seek / header-data offset |
| 9 | light channel |

Current reader support:

- parse_puniu_dat_header(path) is independent and testable.
- Validates channel_count, n_samples, dt_s, seek, file size, and float32 payload alignment.
- Converts timestamp seconds + nanoseconds to UTC datetime when possible.
- read(path, time_slice=None, channel_slice=None, downsample=None) supports basic slicing and stride downsampling.
- Output data is always (n_samples, n_channels).
- metadata.extra_attrs keeps data_format, timestamp fields, seek, light_channel, and raw_header_bytes.

## Deferred formats

- Generic HDF5.
- TXT/CSV small arrays.
- NPY/NPZ.
- SEGY.
- SAC.
- TDMS.

SEGY, SAC, and TDMS should remain optional until the first-priority formats are stable.
