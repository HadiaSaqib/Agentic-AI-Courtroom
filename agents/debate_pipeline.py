from typing import List, Dict
from agents.prosecutor import ProsecutorAgent
from agents.defense import DefenseAgent
from agents.judge import JudgeAgent
from agents.memory import MemoryManager
from models.pydantic_models import JudgementModel
from database.logger import (
    start_debate,
    end_debate,
    log_agent_turn
)

class DebatePipeline:
    """
    Orchestrates a courtroom-style debate:
    Prosecutor → Defense → Judge
    """

    def __init__(self, llm, debate_id: str):
        self.debate_id = debate_id
        self.llm = llm

        # Shared memory across agents
        self.memory = MemoryManager(max_turns=5)

        self.prosecutor = ProsecutorAgent(
            name="prosecutor",
            llm=llm
        )
        self.defense = DefenseAgent(
            name="defense",
            llm=llm
        )
        self.judge = JudgeAgent(
            name="judge",
            llm=llm
        )

        self.evidence_list: List[Dict] = []
        self.hearing_log: List[Dict] = []

    # ----------------------------------
    # Evidence submission
    # ----------------------------------
    def submit_evidence(self, evidence: Dict):
        """
        Evidence is a dict from fact_witness:
        {chunk_id, source, text, score}
        """
        self.evidence_list.append(evidence)

    # ----------------------------------
    # Main debate execution
    # ----------------------------------
    def run(self, case_facts: str, rounds: int = 1) -> JudgementModel:
        """
        Runs debate and returns validated JudgementModel
        """
        start_debate(self.debate_id, case_id="AUTO-CASE")

        # Store case in memory
        self.memory.set_case(case_facts)

        prosecutor_text = ""
        defense_text = ""

        for _ in range(rounds):

            # Prosecutor turn
            prosecutor_text = self.prosecutor.generate_argument(
                case=case_facts,
                evidence_list=self.evidence_list,
                memory=self.memory
            )

            self.memory.add_turn("prosecutor", prosecutor_text)
            self.hearing_log.append({
                "agent": "prosecutor",
                "text": prosecutor_text
            })

            # Defense turn
            defense_text = self.defense.generate_argument(
                case=case_facts,
                evidence_list=self.evidence_list,
                memory=self.memory
            )

            self.memory.add_turn("defense", defense_text)
            self.hearing_log.append({
                "agent": "defense",
                "text": defense_text
            })

        # Judge evaluation
        judgement = self.judge.evaluate(
            debate_id=self.debate_id,
            case=case_facts,
            prosecutor_argument=prosecutor_text,
            defense_argument=defense_text,
            evidence_list=self.evidence_list,
            hearing_log=self.hearing_log
        )

        return judgement

    # ----------------------------------
    # Convenience wrapper
    # ----------------------------------
    def run_and_get_dict(self, case_facts: str, rounds: int = 1) -> dict:
        return self.run(case_facts, rounds).dict()
