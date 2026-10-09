from app import llm, schemas
from app.agents.checklist import build_checklist
from tests.fakes import FakeLLM

Item, Checklist = schemas.ChecklistItem, schemas.Checklist
REQUIRED = ["GST certificate", "PAN card"]


def run(monkeypatch, outputs, required=REQUIRED, stored=("gst.pdf", "pan.pdf")):
    fake = FakeLLM(outputs)
    monkeypatch.setattr(llm, "get_llm", fake.factory)
    return fake, build_checklist(list(required), list(stored))


def test_two_passes_second_is_verification(monkeypatch):
    pass1 = Checklist(items=[Item(document="GST certificate", status="have", matched_file="gst.pdf"),
                             Item(document="PAN card", status="have", matched_file="pan.pdf")])
    pass2 = Checklist(items=[Item(document="GST certificate", status="have", matched_file="gst.pdf"),
                             Item(document="PAN card", status="need")])
    fake, result = run(monkeypatch, [pass1, pass2])
    assert set(fake.agents) == {"checklist"}
    assert len(fake.calls) == 2
    assert all(schema is Checklist for schema, _ in fake.calls)
    assert "pan.pdf" in str(fake.calls[1][1])        # pass 1 output is shown to the verifier
    assert [i.status for i in result.items] == ["have", "need"]


def test_unknown_file_downgraded(monkeypatch):
    claim = Checklist(items=[Item(document="ISO 9001", status="have", matched_file="iso.pdf")])
    _, result = run(monkeypatch, [claim, claim], required=["ISO 9001"], stored=["gst.pdf"])
    assert result.items[0].status == "need" and result.items[0].matched_file is None


def test_verifier_drops_item_keeps_pass1(monkeypatch):
    pass1 = Checklist(items=[Item(document="GST certificate", status="have", matched_file="gst.pdf"),
                             Item(document="PAN card", status="have", matched_file="pan.pdf")])
    pass2 = Checklist(items=[Item(document="GST certificate", status="have", matched_file="gst.pdf")])
    _, result = run(monkeypatch, [pass1, pass2])
    assert [(i.document, i.status, i.matched_file) for i in result.items] == [
        ("GST certificate", "have", "gst.pdf"), ("PAN card", "have", "pan.pdf")]


def test_doc_missing_from_both_passes_is_need(monkeypatch):
    empty = Checklist(items=[])
    _, result = run(monkeypatch, [empty, empty], required=["PAN card"])
    assert [(i.document, i.status) for i in result.items] == [("PAN card", "need")]


def test_no_required_docs_no_call(monkeypatch):
    fake, result = run(monkeypatch, [], required=[])
    assert result.items == [] and fake.calls == []
