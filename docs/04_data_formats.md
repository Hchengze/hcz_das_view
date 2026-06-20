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
- Phase 2C scalarizes numpy scalar attributes and decodes UTF-8 byte attributes where possible.
- Missing raw dataset errors include the expected path.
- Empty time/channel selections raise ReaderError with axis-specific messages.

Orientation logic:

- If raw_shape == (Count, NumberOfLoci), raw orientation is time_channel.
- If raw_shape == (NumberOfLoci, Count), raw orientation is channel_time and the reader transposes to internal convention.
- If only one hint exists, it must match exactly one axis.
- If orientation is ambiguous or cannot be inferred from Count/NumberOfLoci, the reader raises ReaderError instead of guessing.
- Count/NumberOfLoci mismatches with raw_shape are treated as cannot-infer errors;
  the reader does not silently guess orientation.

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
- Phase 2C validates incomplete headers, non-finite numeric header fields,
  seek offsets, float32 payload alignment, payload length mismatches, and empty
  selections with clearer ReaderError messages.
- Timestamp conversion failures return start_time=None instead of crashing metadata reads.

## Real/quasi-real local validation

- examples/validate_file.py validates one file by reading metadata, creating a
  bounded preview, optionally saving a waterfall image, and optionally saving a
  waveform image.
- examples/validate_local_samples.py reads ignored local_validation_paths.txt and
  batch-validates local files without committing inputs or outputs.
- Phase 2C prepared these tools and ran the no-path-list smoke path. No real
  sample paths or generated images were committed.

## Deferred formats

- Generic HDF5.
- TXT/CSV small arrays.
- NPY/NPZ.
- SEGY.
- SAC.
- TDMS.

SEGY, SAC, and TDMS should remain optional until the first-priority formats are stable.
