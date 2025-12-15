import uuid
from typing import List, Dict
from models.pydantic_models import JudgementModel
from rag.fact_witness import fact_witness_answer
from database.logger import log_judgement

class JudgeAgent:
    """
    Judge evaluates prosecutor & defense arguments using evidence(details) provided by case details and compares it with evidence_list
    and returns a structured JudgementModel.
    """

    def __init__(self, name: str = "judge", llm=None):
        self.name = name
        self.llm = llm

    # ----------------------------------
    # Simple scoring logic (deterministic)
    # ----------------------------------
    def _score_arguments(
        self,
        prosecutor_text: str,
        defense_text: str,
        evidence: List[Dict]
    ) -> Dict[str, float]:

        evidence_score = min(sum(e.get("score", 0) for e in evidence) * 100, 100)

        scores = {
            "evidence_strength": round(evidence_score, 2),
            "legal_reasoning": 80 if "law" in prosecutor_text.lower() else 60,
            "counter_arguments": 70 if "however" in defense_text.lower() else 50,
            "clarity": min(len(prosecutor_text.split()), 100)
        }
        return scores

    # ----------------------------------
    # Judge deliberation
    # ----------------------------------
    def deliberate(
        self,
        verdict: str,
        case: str,
        prosecutor_argument: str,
        defense_argument: str
    ) -> str:
        """
        LLM generates reasoning but MUST respect the given verdict
        """

        prompt = f"""
    You are a judge in a traffic law courtroom.

    RULES:
    - Verdict is FINAL and cannot be changed
    - Max 150 words
    - No repetition of arguments
    - Be formal and concise
    - Give fine if any in PKR and according to pakistan traffic rules 
    -fine amount must be less than 5000

    FINAL VERDICT: {verdict}

    CASE FACTS:
    {case}


    PROSECUTOR SUMMARY:
    {prosecutor_argument[:300]}

    DEFENSE SUMMARY:
    {defense_argument[:300]}

    Provide legal reasoning and punishment (if applicable).
    """

        if self.llm:
            return self.llm(prompt)

        return f"The court finds: {verdict}."

    # ----------------------------------
    # Full evaluation → structured output
    # ----------------------------------
    def evaluate(
        self,
        debate_id: str,
        case: str,
        prosecutor_argument: str,
        defense_argument: str,
        evidence_list: List[Dict],
        hearing_log: List[Dict]
    ) -> JudgementModel:

        scores = self._score_arguments(
            prosecutor_argument,
            defense_argument,
            evidence_list
        )

        verdict = (
            "Violation Confirmed"
            if scores["evidence_strength"] >= 60
            else "Violation Not Confirmed"
        )

        reasoning = self.deliberate(
        verdict,
        case,
        prosecutor_argument,
        defense_argument
        )
        log_judgement(
            debate_id=debate_id,
            scores=scores,
            verdict=verdict
        )


        return JudgementModel(
            judgement_id=str(uuid.uuid4()),
            case_id="AUTO-CASE",
            verdict=verdict,
            prosecution_score=scores["evidence_strength"],
            defense_score=100 - scores["evidence_strength"],
            rubric_scores=scores,
            reasoning=reasoning,
            case_facts=case,
            evidence_considered=evidence_list,
            hearing_log=hearing_log
        )
