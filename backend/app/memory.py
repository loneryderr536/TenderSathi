"""ChromaDB vector memory: tender clauses and business details (the RAG layer)."""
import chromadb

from app.schemas import Clause


class Memory:
    def __init__(self, path: str, embedding_function=None):
        client = chromadb.PersistentClient(path=path)
        kwargs = {"embedding_function": embedding_function} if embedding_function else {}
        self.clauses = client.get_or_create_collection("clauses", **kwargs)
        self.business = client.get_or_create_collection("business", **kwargs)

    def add_clauses(self, tender_id: int, clauses: list[Clause]) -> None:
        """Replace this tender's clauses (so reruns don't duplicate)."""
        self.clauses.delete(where={"tender_id": tender_id})
        if clauses:
            self.clauses.add(
                ids=[f"{tender_id}-{i}" for i in range(len(clauses))],
                documents=[c.text for c in clauses],
                metadatas=[{"tender_id": tender_id, "clause": c.clause, "page": c.page} for c in clauses],
            )

    def search_clauses(self, tender_id: int, query: str, k: int = 4) -> list[Clause]:
        result = self.clauses.query(query_texts=[query], n_results=k, where={"tender_id": tender_id})
        return [Clause(text=doc, clause=meta["clause"], page=meta["page"])
                for doc, meta in zip(result["documents"][0], result["metadatas"][0])]

    def add_business(self, company_id: int, lines: list[str]) -> None:
        """Replace this company's business details."""
        self.business.delete(where={"company_id": company_id})
        if lines:
            self.business.add(
                ids=[f"{company_id}-{i}" for i in range(len(lines))],
                documents=lines,
                metadatas=[{"company_id": company_id} for _ in lines],
            )

    def search_business(self, company_id: int, query: str, k: int = 3) -> list[str]:
        result = self.business.query(query_texts=[query], n_results=k, where={"company_id": company_id})
        return result["documents"][0]
