import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

llm = ChatOpenAI(
    model="meta-llama/llama-3.1-8b-instruct",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0.3,
)

def lc_llm(prompt: str) -> str:
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content