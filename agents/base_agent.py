class BaseAgent:
    """
    Base class for all debate agents.
    """

    def __init__(self, name: str, llm):
        self.name = name
        self.llm = llm

    def generate(self, prompt: str) -> str:
        """
        Sends a prompt to the LLM.
        """
        return self.llm(prompt)