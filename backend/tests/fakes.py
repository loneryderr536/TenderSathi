"""Fake chat model for agent tests: returns preset outputs and records every call."""


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
