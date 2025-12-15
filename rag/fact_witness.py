from rag.retriever import retrieve

def fact_witness_answer(query: str):
    return retrieve(query)
