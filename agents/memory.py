from database.logger import log_memory


class MemoryManager:
    """
    Stores:
    - last 5 debate turns
    - case info
    - long-term memory placeholder
    """

    def __init__(self, max_turns: int = 5):
        self.case_summary = None
        self.turn_history = []
        self.max_turns = max_turns

    def set_case(self, case_text: str):
        self.case_summary = case_text

    def add_turn(self, speaker: str, text: str, debate_id=None):
        self.turn_history.append({"speaker": speaker, "text": text})    
        if debate_id:
            log_memory(debate_id, speaker, text)
        if len(self.turn_history) > self.max_turns:
            self.turn_history.pop(0)

    def get_memory_prompt(self) -> str:
        """
        Converts memory into text for prompt injection.
        """
        memory_text = "\n".join(
            [f"{t['speaker']}: {t['text']}" for t in self.turn_history]
        )

        return (
            f"CASE SUMMARY:\n{self.case_summary}\n\n"
            f"RECENT DEBATE MEMORY:\n{memory_text}\n"
        )