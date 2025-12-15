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

    # Evidence relevance (0–100)
    evidence_strength = min(
        sum(e.get("score", 0) for e in evidence) * 100,
        100
    )

    # Prosecutor legal application
    legal_application = 70
    legal_keywords = ["law", "section", "act", "rule", "traffic", "penalty", "fine"]
    if any(k in prosecutor_text.lower() for k in legal_keywords):
        legal_application += 20
    legal_application = min(legal_application, 100)

    # Defense rebuttal effectiveness
    defense_effectiveness = 50
    defense_keywords = ["however", "no evidence", "not proven", "lack", "reasonable doubt"]
    if any(k in defense_text.lower() for k in defense_keywords):
        defense_effectiveness += 30
    defense_effectiveness = min(defense_effectiveness, 100)

    # Consistency with facts (length & focus)
    consistency = min(
        (len(prosecutor_text.split()) + len(defense_text.split())) / 4,
        100
    )

    return {
        "evidence_strength": round(evidence_strength, 2),
        "legal_application": round(legal_application, 2),
        "defense_effectiveness": round(defense_effectiveness, 2),
        "consistency": round(consistency, 2)
    }


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

        final_score = (
    scores["evidence_strength"] * 0.4 +
    scores["legal_application"] * 0.3 +
    scores["consistency"] * 0.2 -
    scores["defense_effectiveness"] * 0.3
)

verdict = (
    "Violation Confirmed"
    if final_score >= 60
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
            prosecution_score=round(
    (scores["evidence_strength"] + scores["legal_application"]) / 2,
    2
),
            defense_score=round(scores["defense_effectiveness"], 2),

            rubric_scores=scores,
            reasoning=reasoning,
            case_facts=case,
            evidence_considered=evidence_list,
            hearing_log=hearing_log
        )

