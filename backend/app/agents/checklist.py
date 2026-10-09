"""Checklist agent: maps required documents to stored files and flags gaps."""
from app import llm
from app.schemas import Checklist, ChecklistItem

MATCH_PROMPT = """Match each document a government tender requires to one of the business's stored files.
For each required document return: the document name exactly as given, status "have" with the
matched file name, or status "need" if no stored file is that document.

Required documents:
{required}

Stored files:
{stored}"""

VERIFY_PROMPT = """Double-check this document checklist for a government tender bid.
For each required document, confirm the match is correct. If a "have" points to a file that is
not clearly that document, or to a file not in the stored list, correct it to "need".
If a "need" actually has a matching stored file, correct it to "have".
Return the full corrected checklist, using each document name exactly as given.

Required documents:
{required}

Stored files:
{stored}

Checklist to verify:
{checklist}"""


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


def build_checklist(required_docs: list[str], stored_docs: list[str]) -> Checklist:
    """Two Haiku passes: match, then double-check the match."""
    if not required_docs:
        return Checklist(items=[])
    model = llm.get_llm("checklist").with_structured_output(Checklist)
    required, stored = _bullets(required_docs), _bullets(stored_docs)

    first = model.invoke(MATCH_PROMPT.format(required=required, stored=stored))
    checked = model.invoke(VERIFY_PROMPT.format(
        required=required, stored=stored,
        checklist=_bullets([f"{i.document}: {i.status} ({i.matched_file or 'no file'})" for i in first.items]),
    ))

    first_by_doc = {i.document: i for i in first.items}
    checked_by_doc = {i.document: i for i in checked.items}
    items = []
    for doc in required_docs:
        item = checked_by_doc.get(doc) or first_by_doc.get(doc)
        # A "have" must point at a file the business actually holds.
        if item is None or item.status != "have" or item.matched_file not in stored_docs:
            item = ChecklistItem(document=doc, status="need")
        items.append(item)
    return Checklist(items=items)
