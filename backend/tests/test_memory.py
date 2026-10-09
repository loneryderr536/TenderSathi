import pytest

from app.memory import Memory
from app.schemas import Clause
from tests.fakes import HashEmbedding

TURNOVER = Clause(text="Turnover of Rs 1 crore", clause="4.1", page=7)
ISO = Clause(text="ISO 9001 certificate", clause="4.2", page=8)


@pytest.fixture
def mem(tmp_path):
    return Memory(str(tmp_path), embedding_function=HashEmbedding())


def test_search_clauses_scoped_to_tender(mem):
    mem.add_clauses(1, [TURNOVER, ISO])
    mem.add_clauses(2, [Clause(text="Turnover of Rs 5 crore", clause="3.1", page=2)])
    assert mem.search_clauses(1, "turnover", k=1) == [TURNOVER]


def test_add_clauses_replaces_on_rerun(mem):
    mem.add_clauses(1, [TURNOVER, ISO])
    mem.add_clauses(1, [ISO])
    assert mem.search_clauses(1, "turnover", k=10) == [ISO]


def test_empty_memory_returns_empty(mem):
    assert mem.search_clauses(5, "anything") == []


def test_warm_up_runs_the_embedding_once(tmp_path):
    calls = []

    class Counting(HashEmbedding):
        def __call__(self, input):
            calls.append(list(input))
            return super().__call__(input)

    Memory(str(tmp_path), embedding_function=Counting()).warm_up()
    assert len(calls) == 1


def test_warm_up_never_raises(tmp_path, monkeypatch):
    m = Memory(str(tmp_path), embedding_function=HashEmbedding())
    monkeypatch.setattr(m.clauses, "query", lambda **kw: (_ for _ in ()).throw(RuntimeError("offline")))
    assert m.warm_up() is False
