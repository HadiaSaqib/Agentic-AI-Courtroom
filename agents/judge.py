import uuid
from typing import List, Dict
from models.pydantic_models import JudgementModel
from rag.fact_witness import fact_witness_answer
from database.logger import log_judgement


class JudgeAgent:
    """
    Judge evaluates prosecutor & defense arguments using structured rubric scoring
    and produces a final JudgementModel with possible benefit of doubt.
    """

    def __init__(self, name: str = "judge", llm=None):
        self.name = name
        self.llm = llm

    # ----------------------------------
    # Improved Rubric Scoring (0–100)
    # ----------------------------------
    def _score_arguments(
        self,
        prosecutor_text: str,
        defense_text: str,
        evidence: List[Dict],
        case_facts: str
    ) -> Dict[str, float]:

        # 1. Evidence Strength
        evidence_strength = min(sum(e.get("score", 0) for e in evidence) * 100, 100)

        # 2. Prosecutor Legal Application
        legal_application = 50
        legal_keywords = [
            "law", "section", "act", "rule",
            "traffic", "penalty", "fine",
            "violation", "offence"
        ]
        if any(k in prosecutor_text.lower() for k in legal_keywords):
            legal_application += 25
        legal_application = min(legal_application, 100)

        # 3. Defense Effectiveness
        defense_effectiveness = 50
        defense_keywords = [
            "however", "no evidence", "not proven",
            "reasonable doubt", "lack", "insufficient",
            "no witness", "procedural error"
        ]
        if any(k in defense_text.lower() for k in defense_keywords):
            defense_effectiveness += 20
        defense_effectiveness = min(defense_effectiveness, 100)

        # 4. Consistency with Case Facts (keyword matching)
        case_words = set(word.lower() for word in case_facts.split())
        prosecutor_words = set(word.lower() for word in prosecutor_text.split())
        defense_words = set(word.lower() for word in defense_text.split())

        matches = len(case_words & (prosecutor_words | defense_words))
        consistency = min((matches / len(case_words)) * 100, 100) if case_words else 50

        # 5. Credibility of Evidence
        credibility = 50
        if evidence and any(e.get("verified", False) for e in evidence):
            credibility += 20
        credibility = min(credibility, 100)

        return {
            "evidence_strength": round(evidence_strength, 2),
            "legal_application": round(legal_application, 2),
            "defense_effectiveness": round(defense_effectiveness, 2),
            "consistency": round(consistency, 2),
            "credibility": round(credibility, 2)
        }

    # ----------------------------------
    # Judge Deliberation (LLM reasoning)
    # ----------------------------------
    def deliberate(
        self,
        verdict: str,
        case: str,
        confidence:float,
        prosecutor_argument: str,
        defense_argument: str
    ) -> str:
        """
        LLM generates reasoning but MUST respect final verdict.
        """

        prompt = f"""
You are a judge in a Pakistani traffic law courtroom.

RULES:
- Verdict and confidence are FINAL and cannot be changed
- Max 150 words
- No repetition
- Formal judicial tone
- Mention applicable fine from pakistan traffic rules(PKR, less than 5000)
- must mention confidence explicitly

FINAL VERDICT:
{verdict}

Confidence:
{confidence}

CASE FACTS:
{case}

PROSECUTOR SUMMARY:
{prosecutor_argument[:300]}

DEFENSE SUMMARY:
{defense_argument[:300]}

Provide legal reasoning and punishment (if applicable).
Mention confidence explicitly.
"""

        if self.llm:
            return self.llm(prompt)

        return f"The court finds: {verdict} having {confidence}  based on the presented facts and evidence."

    # ----------------------------------
    # Full Evaluation → Structured Output
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
            evidence_list,
            case
        )

        # Weighted Final Score
        final_score = (
            scores["evidence_strength"] * 0.35 +
            scores["legal_application"] * 0.25 +
            scores["consistency"] * 0.15 +
            scores["credibility"] * 0.25 -
            scores["defense_effectiveness"] * 0.2
        )

        # Weighted prosecution score
        prosecution_score = (scores["evidence_strength"] + scores["legal_application"]) / 2
        defense_score=round(scores["defense_effectiveness"], 2)
        # ----------------------------------
        # Verdict Logic with thresholds 
        # ----------------------------------
        
        if  prosecution_score>defense_score:
            verdict = "Violation  Confirmed"
        elif  prosecution_score<defense_score:
            verdict = "Violation Not Confirmed"
        else   verdict = "Benefit of doubt granted"
     
        confidence=final_score
        reasoning = self.deliberate(
            verdict,
            case,
            confidence,
            prosecutor_argument,
            defense_argument
        )

        # Log judgement
        log_judgement(
            debate_id=debate_id,
            scores=scores,
            verdict=verdict,
            
        )

        return JudgementModel(
            judgement_id=str(uuid.uuid4()),
            case_id="AUTO-CASE",
            verdict=verdict,
            prosecution_score=round(prosecution_score, 2),
            defense_score=round(scores["defense_effectiveness"], 2),
            rubric_scores=scores,
            reasoning=reasoning,
            case_facts=case,
            evidence_considered=evidence_list,
            hearing_log=hearing_log,
            
        )







