"""Tests for the internal experimental vector-store foundation."""

from __future__ import annotations

import math

import pytest

from mellivor_kernel.memory._vector import (
    InMemoryVectorStore,
    VectorMatch,
    VectorRecord,
    VectorStore,
    VectorStoreError,
)


def _record(
    record_id: str,
    vector: tuple[float, ...],
    metadata: object = None,
) -> VectorRecord:
    return VectorRecord(
        id=record_id,
        vector=vector,
        metadata={} if metadata is None else metadata,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("dimensions", [0, -1, True, 1.5])
def test_store_requires_positive_integer_dimensions(dimensions: object) -> None:
    with pytest.raises(VectorStoreError):
        InMemoryVectorStore(dimensions)  # type: ignore[arg-type]


def test_store_conforms_to_protocol_and_exposes_dimensions() -> None:
    store = InMemoryVectorStore(3)

    assert isinstance(store, VectorStore)
    assert store.dimensions == 3


@pytest.mark.parametrize("record_id", ["", "   ", 1, None])
def test_record_requires_nonblank_string_id(record_id: object) -> None:
    with pytest.raises(VectorStoreError):
        VectorRecord(id=record_id, vector=(1.0,))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "vector",
    [(), (0.0, 0.0), (math.nan,), (math.inf,), (-math.inf,), (True,), ("1",)],
)
def test_record_rejects_invalid_vectors(vector: object) -> None:
    with pytest.raises(VectorStoreError):
        VectorRecord(id="record", vector=vector)  # type: ignore[arg-type]


def test_record_normalizes_vector_and_redacts_repr() -> None:
    record = VectorRecord(id="record", vector=(1, 2.5))

    assert record.vector == (1.0, 2.5)
    assert "1.0" not in repr(record)


def test_metadata_is_scalar_only_defensive_and_redacted() -> None:
    source: dict[str, object] = {
        "text": "private-metadata",
        "count": 2,
        "ratio": 1.5,
        "enabled": True,
        "optional": None,
    }
    record = VectorRecord(id="record", vector=(1.0,), metadata=source)  # type: ignore[arg-type]
    source["text"] = "mutated"

    assert record.metadata["text"] == "private-metadata"
    assert "private-metadata" not in repr(record)
    with pytest.raises(TypeError):
        record.metadata["text"] = "forbidden"  # type: ignore[index]


@pytest.mark.parametrize(
    "metadata",
    [
        {"": "value"},
        {"   ": "value"},
        {1: "value"},
        {"nested": {"key": "value"}},
        {"sequence": [1, 2]},
        {"tuple": (1, 2)},
        {"object": object()},
        {"nan": math.nan},
        {"infinity": math.inf},
        ["not", "mapping"],
    ],
)
def test_metadata_rejects_nonportable_values_without_echoing_them(metadata: object) -> None:
    with pytest.raises(VectorStoreError) as exc_info:
        VectorRecord(id="record", vector=(1.0,), metadata=metadata)  # type: ignore[arg-type]

    assert "nested" not in str(exc_info.value)
    assert "object" not in str(exc_info.value)


def test_vector_match_validates_score_and_redacts_metadata() -> None:
    match = VectorMatch(id="record", score=1, metadata={"secret": "private"})

    assert match.score == 1.0
    assert not hasattr(match, "vector")
    assert "private" not in repr(match)


@pytest.mark.parametrize("score", [math.nan, math.inf, -1.1, 1.1, True, "1"])
def test_vector_match_rejects_invalid_scores(score: object) -> None:
    with pytest.raises(VectorStoreError):
        VectorMatch(id="record", score=score)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "namespace",
    ["", "-leading", ".leading", "with space", "tenant/slash", "a" * 129, 1, None],
)
def test_namespace_validation(namespace: object) -> None:
    store = InMemoryVectorStore(1)

    with pytest.raises(VectorStoreError) as exc_info:
        store.fetch((), namespace=namespace)  # type: ignore[arg-type]

    if namespace != "":
        assert str(namespace) not in str(exc_info.value)


def test_valid_namespace_characters() -> None:
    store = InMemoryVectorStore(1)

    store.upsert((_record("id", (1.0,)),), namespace="Tenant_1.prod-test")

    assert store.fetch(("id",), namespace="Tenant_1.prod-test")[0].id == "id"


def test_upsert_fetch_and_replacement() -> None:
    store = InMemoryVectorStore(2)
    store.upsert((_record("a", (1.0, 0.0), {"version": 1}),), namespace="tenant")
    store.upsert((_record("a", (0.0, 1.0), {"version": 2}),), namespace="tenant")

    fetched = store.fetch(("a",), namespace="tenant")

    assert fetched[0].vector == (0.0, 1.0)
    assert fetched[0].metadata["version"] == 2


def test_upsert_validates_entire_batch_before_mutation() -> None:
    store = InMemoryVectorStore(2)
    original = _record("existing", (1.0, 0.0))
    store.upsert((original,), namespace="tenant")

    with pytest.raises(VectorStoreError):
        store.upsert(
            (_record("valid", (1.0, 0.0)), _record("invalid", (1.0, 0.0, 0.0))),
            namespace="tenant",
        )

    assert store.fetch(("existing", "valid", "invalid"), namespace="tenant") == (original,)


def test_upsert_rejects_duplicate_ids_atomically() -> None:
    store = InMemoryVectorStore(2)

    with pytest.raises(VectorStoreError):
        store.upsert(
            (_record("duplicate", (1.0, 0.0)), _record("duplicate", (0.0, 1.0))),
            namespace="tenant",
        )

    assert store.fetch(("duplicate",), namespace="tenant") == ()


def test_upsert_requires_nonempty_tuple() -> None:
    store = InMemoryVectorStore(1)

    with pytest.raises(VectorStoreError):
        store.upsert((), namespace="tenant")


def test_exact_cosine_query_and_score_range() -> None:
    store = InMemoryVectorStore(2)
    store.upsert(
        (
            _record("same", (1.0, 0.0)),
            _record("diagonal", (1.0, 1.0)),
            _record("orthogonal", (0.0, 1.0)),
            _record("opposite", (-1.0, 0.0)),
        ),
        namespace="tenant",
    )

    matches = store.query((1.0, 0.0), namespace="tenant", limit=10)

    assert [match.id for match in matches] == ["same", "diagonal", "orthogonal", "opposite"]
    assert matches[0].score == pytest.approx(1.0)
    assert matches[1].score == pytest.approx(math.sqrt(0.5))
    assert matches[2].score == pytest.approx(0.0)
    assert matches[3].score == pytest.approx(-1.0)
    assert all(-1.0 <= match.score <= 1.0 for match in matches)


def test_query_ties_break_by_ascending_id() -> None:
    store = InMemoryVectorStore(2)
    store.upsert((_record("z", (1.0, 1.0)), _record("a", (1.0, 1.0))), namespace="tenant")

    matches = store.query((1.0, 0.0), namespace="tenant", limit=2)

    assert [match.id for match in matches] == ["a", "z"]


@pytest.mark.parametrize(
    ("vector", "limit"),
    [
        ((1.0,), 1),
        ((0.0, 0.0), 1),
        ((math.nan, 1.0), 1),
        ((math.inf, 1.0), 1),
        ((1.0, 0.0), 0),
        ((1.0, 0.0), True),
    ],
)
def test_query_rejects_invalid_vector_dimension_or_limit(vector: object, limit: object) -> None:
    store = InMemoryVectorStore(2)

    with pytest.raises(VectorStoreError):
        store.query(vector, namespace="tenant", limit=limit)  # type: ignore[arg-type]


def test_query_empty_namespace_returns_empty() -> None:
    store = InMemoryVectorStore(2)

    assert store.query((1.0, 0.0), namespace="tenant", limit=1) == ()


def test_fetch_preserves_order_and_omits_missing_ids() -> None:
    store = InMemoryVectorStore(1)
    first = _record("first", (1.0,))
    second = _record("second", (1.0,))
    store.upsert((first, second), namespace="tenant")

    assert store.fetch(("second", "missing", "first"), namespace="tenant") == (
        second,
        first,
    )
    assert store.fetch((), namespace="tenant") == ()


def test_fetch_and_delete_reject_duplicate_or_invalid_ids() -> None:
    store = InMemoryVectorStore(1)

    for operation in (store.fetch, store.delete):
        with pytest.raises(VectorStoreError):
            operation(("duplicate", "duplicate"), namespace="tenant")
        with pytest.raises(VectorStoreError):
            operation(("",), namespace="tenant")


def test_delete_is_idempotent_and_namespace_scoped() -> None:
    store = InMemoryVectorStore(1)
    left = _record("shared", (1.0,), {"scope": "left"})
    right = _record("shared", (1.0,), {"scope": "right"})
    store.upsert((left,), namespace="left")
    store.upsert((right,), namespace="right")

    store.delete(("shared",), namespace="left")
    store.delete(("shared", "missing"), namespace="left")
    store.delete((), namespace="left")

    assert store.fetch(("shared",), namespace="left") == ()
    assert store.fetch(("shared",), namespace="right") == (right,)


def test_query_and_fetch_are_namespace_isolated() -> None:
    store = InMemoryVectorStore(2)
    store.upsert((_record("left", (1.0, 0.0)),), namespace="left")
    store.upsert((_record("right", (1.0, 0.0)),), namespace="right")

    assert [match.id for match in store.query((1.0, 0.0), namespace="left", limit=10)] == ["left"]
    assert store.fetch(("right",), namespace="left") == ()


def test_errors_and_reprs_do_not_expose_vector_or_metadata_values() -> None:
    private_vector = (123456.789,)
    private_metadata = "metadata-secret"
    record = _record("record", private_vector, {"secret": private_metadata})
    store = InMemoryVectorStore(2)

    with pytest.raises(VectorStoreError) as exc_info:
        store.upsert((record,), namespace="tenant")

    diagnostic = f"{record!r} {exc_info.value!s}"
    assert "123456.789" not in diagnostic
    assert private_metadata not in diagnostic
