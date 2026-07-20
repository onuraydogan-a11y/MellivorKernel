from mellivor_kernel import __version__


def test_version_is_a_non_empty_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_version_follows_semver_shape() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
