"""Test fakes: a chat model that returns preset outputs, and an offline embedding."""
import hashlib
import re

from chromadb import Documents, EmbeddingFunction, Embeddings


class FakeLLM:
    def __init__(self, outputs):
        self.outputs, self.calls, self.agents = list(outputs), [], []

    def factory(self, agent):          # monkeypatch target for app.llm.get_llm
        self.agents.append(agent)
        return self

    def with_structured_output(self, schema):
        fake = self

        class _Runnable:
            def invoke(self, prompt):
                fake.calls.append((schema, prompt))
                return fake.outputs.pop(0)

        return _Runnable()


class HashEmbedding(EmbeddingFunction[Documents]):
    """Offline embedding for tests: normalised hashed word counts in 64 dimensions."""

    def __init__(self):
        pass

    @staticmethod
    def name() -> str:
        return "hash-test"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "HashEmbedding":
        return HashEmbedding()

    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for doc in input:
            v = [0.0] * 64
            for word in re.findall(r"\w+", doc.lower()):
                v[int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
            norm = sum(x * x for x in v) ** 0.5 or 1.0
            vectors.append([x / norm for x in v])   # unit length, so L2 ranks like cosine
        return vectors
