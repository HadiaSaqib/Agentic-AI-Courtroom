from .base_agent import BaseAgent
from .argument_utils import build_argument_prompt, classify_argument_prompt, summarize_prompt

class ProsecutorAgent(BaseAgent):

    def generate_argument(self, case, evidence_list, memory):
        prompt = build_argument_prompt(
            role="Prosecutor",
            case=case,
            evidence_list=evidence_list,
            memory_text=memory.get_memory_prompt()
        )
        argument = self.generate(prompt)
        memory.add_turn("Prosecutor", argument)
        return argument

    def classify(self, argument):
        return self.generate(classify_argument_prompt(argument))

    def summarize(self, argument):
        return self.generate(summarize_prompt(argument))
