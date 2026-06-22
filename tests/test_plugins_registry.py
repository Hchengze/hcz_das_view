import pytest

from das_view.plugins.base import ExtensionMetadata
from das_view.plugins.registry import (
    ExtensionRegistry,
    clear_extensions,
    discover_entry_point_extensions,
    get_global_registry,
    list_extensions,
    register_extension,
)


def _metadata(name="demo", kind="analysis", *, enabled=True):
    return ExtensionMetadata(name=name, kind=kind, enabled=enabled)


def test_registry_register_list_get_and_unregister():
    registry = ExtensionRegistry()
    extension = _metadata()

    registry.register(extension)

    assert registry.get("demo") is extension
    assert registry.list() == [extension]
    assert registry.unregister("demo") is extension
    assert registry.list() == []


def test_registry_filters_by_kind_and_enabled():
    registry = ExtensionRegistry()
    registry.register(_metadata("enabled_reader", "reader", enabled=True))
    registry.register(_metadata("disabled_reader", "reader", enabled=False))
    registry.register(_metadata("analysis", "analysis", enabled=True))

    assert [item.name for item in registry.list(kind="reader")] == [
        "disabled_reader",
        "enabled_reader",
    ]
    assert [item.name for item in registry.list(enabled=True)] == [
        "analysis",
        "enabled_reader",
    ]


def test_registry_duplicate_requires_replace():
    registry = ExtensionRegistry()
    registry.register(_metadata(description := "demo"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_metadata(description))

    replacement = _metadata(description, "processing")
    registry.register(replacement, replace=True)
    assert registry.get(description) is replacement


def test_registry_clear():
    registry = ExtensionRegistry()
    registry.register(_metadata())

    registry.clear()

    assert len(registry) == 0


def test_global_registry_helpers_do_not_pollute_isolated_registry():
    isolated = ExtensionRegistry()
    clear_extensions()
    register_extension(_metadata("global_demo"))
    register_extension(_metadata("isolated_demo"), registry=isolated)

    assert [item.name for item in list_extensions()] == ["global_demo"]
    assert [item.name for item in list_extensions(registry=isolated)] == ["isolated_demo"]
    assert get_global_registry() is not isolated
    clear_extensions()


class _FakeEntryPoints:
    def __init__(self, values):
        self._values = values

    def select(self, *, group):
        assert group == "das_view.plugins"
        return self._values


class _FailingEntryPoint:
    name = "broken"

    def load(self):
        raise RuntimeError("boom")


def test_entry_point_discovery_empty_does_not_crash(monkeypatch):
    import das_view.plugins.registry as registry_module

    monkeypatch.setattr(
        registry_module.importlib_metadata,
        "entry_points",
        lambda: _FakeEntryPoints([]),
    )
    registry = ExtensionRegistry()

    result = discover_entry_point_extensions(registry=registry)

    assert result.registered == []
    assert result.failed == []
    assert registry.list() == []


def test_entry_point_discovery_records_loading_failure(monkeypatch):
    import das_view.plugins.registry as registry_module

    monkeypatch.setattr(
        registry_module.importlib_metadata,
        "entry_points",
        lambda: _FakeEntryPoints([_FailingEntryPoint()]),
    )

    result = discover_entry_point_extensions(registry=ExtensionRegistry())

    assert result.registered == []
    assert result.failed == [{"entry_point": "broken", "error": "boom"}]
