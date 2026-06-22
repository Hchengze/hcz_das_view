import pytest

from das_view.plugins.base import (
    AnalysisExtension,
    ExtensionMetadata,
    ReaderExtension,
)


def test_extension_metadata_validates_required_name_and_kind():
    metadata = ExtensionMetadata(name="demo", kind="analysis")

    assert metadata.name == "demo"
    assert metadata.kind == "analysis"
    assert metadata.tags == ()
    assert metadata.enabled is True


def test_extension_metadata_rejects_empty_name():
    with pytest.raises(ValueError, match="name is required"):
        ExtensionMetadata(name=" ", kind="analysis")


def test_extension_metadata_rejects_invalid_kind():
    with pytest.raises(ValueError, match="Invalid extension kind"):
        ExtensionMetadata(name="demo", kind="invalid")


def test_extension_metadata_to_dict_and_from_dict_round_trip():
    metadata = ExtensionMetadata(
        name="demo",
        kind="processing",
        version="1.0",
        description="Demo extension",
        provider="tests",
        module="tests.demo",
        tags=[" demo ", "", "test"],
        enabled=False,
    )

    payload = metadata.to_dict()
    restored = ExtensionMetadata.from_dict(payload)

    assert payload["tags"] == ["demo", "test"]
    assert restored == metadata
    assert restored.enabled is False


def test_reader_extension_basic_construction():
    extension = ReaderExtension(
        metadata=ExtensionMetadata(name="reader_demo", kind="reader"),
        extensions=[".demo"],
        can_read="package.reader.can_read",
    )

    assert extension.metadata.name == "reader_demo"
    assert extension.extensions == (".demo",)
    assert extension.can_read == "package.reader.can_read"


def test_analysis_extension_basic_construction():
    extension = AnalysisExtension(
        metadata=ExtensionMetadata(name="analysis_demo", kind="analysis"),
        function=lambda data: data,
        input_kind="array",
        output_kind="summary",
        parameters_schema={"axis": {"type": "integer"}},
    )

    assert callable(extension.function)
    assert extension.input_kind == "array"
    assert extension.output_kind == "summary"
    assert extension.parameters_schema["axis"]["type"] == "integer"


def test_extension_wrapper_rejects_wrong_kind():
    with pytest.raises(ValueError, match="does not match"):
        ReaderExtension(metadata=ExtensionMetadata(name="bad", kind="analysis"))
