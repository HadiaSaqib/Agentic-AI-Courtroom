import uuid
from typing import List, Dict
from models.pydantic_models import JudgementModel
from database.logger import log_judgement
from rag.fact_witness import fact_witness_answer


class JudgeAgent:
    """
    JudgeAgent evaluates prosecutor & defense arguments using
    an advanced, explainable rubric-based scoring system.

    IMPORTANT DESIGN:
    - Judge does NOT fetch new facts
    - Judge MAY validate original laws (read-only) via RAG
    - Verdict logic remains deterministic
    """

    def __init__(self, name: str = "judge", llm=None):
        self.name = name
        self.llm = llm

    # -----------------------------
    # Utility
    # -----------------------------
    def _tokenize(self, text: str) -> set:
        return {
            w.lower().strip(".,")
            for w in text.split()
            if len(w) > 3
        }

    # -----------------------------
    # LAW VALIDATION (Read-only)
    # -----------------------------
    def _validate_law(self, offence: str) -> Dict:
        """
        Uses RAG ONLY to validate legal limits and sections.
        Does NOT influence guilt determination.
        """
        try:
            result = fact_witness_answer(
                f"Pakistan traffic law section and maximum fine for {offence}"
            )
            if isinstance(result, list) and result:
                return result[0]  # Return first law info if multiple
            if isinstance(result, dict):
                return result
            return {}
        except Exception:
            return {}

    # -----------------------------
    # Evidence Strength (0–100)
    # -----------------------------
    def _calculate_evidence_strength(self, evidence: List[Dict]) -> float:
        if not evidence:
            return 0.0
        credibility = sum(e.get("credibility", 0.5) for e in evidence)
        relevance = sum(e.get("relevance", 0.5) for e in evidence)
        count_bonus = min(len(evidence) * 5, 20)
        score = ((credibility + relevance) * 10) + count_bonus
        return round(min(score, 100), 2)

    # -----------------------------
    # Legal Application (0–100)
    # -----------------------------
    def _calculate_legal_application(
        self, prosecutor_text: str, evidence: List[Dict]
    ) -> float:
        text = prosecutor_text.lower()

        # 1️⃣ Law / Section Citation (0–30)
        law_keywords = [
            "section", "act", "ordinance", "rule",
            "motor vehicle", "traffic law"
        ]
        law_score = 30 if any(k in text for k in law_keywords) else 10

        # 2️⃣ Rule → Fact Reasoning (0–30)
        reasoning_keywords = [
            "therefore", "hence", "thus",
            "as per", "violated", "liable"
        ]
        reasoning_score = 30 if any(k in text for k in reasoning_keywords) else 15

        # 3️⃣ Punishment Alignment (0–25)
        penalty_keywords = ["fine", "penalty", "punishment"]
        penalty_score = 0
        if any(k in text for k in penalty_keywords):
            penalty_score = 15
            if any(e.get("type") == "penalty" for e in evidence):
                penalty_score = 25

        # 4️⃣ Procedural Correctness (0–15)
        procedure_keywords = [
            "challan", "traffic warden",
            "notice issued", "court summons"
        ]
        procedure_score = 15 if any(k in text for k in procedure_keywords) else 5

        total = law_score + reasoning_score + penalty_score + procedure_score
        return round(min(total, 100), 2)

    # -----------------------------
    # Defense Effectiveness (0–100)
    # -----------------------------
    def _calculate_defense_effectiveness(self, defense_text: str) -> float:
        text = defense_text.lower()
        base = 40

        strong_defense_keywords = [
            "reasonable doubt", "no evidence",
            "procedural error", "lack of proof",
            "unreliable witness"
        ]
        if any(k in text for k in strong_defense_keywords):
            base += 20

        mitigation_keywords = [
            "first offense", "emergency",
            "medical", "leniency"
        ]
        if any(k in text for k in mitigation_keywords):
            base += 10

        return round(min(base, 100), 2)

    # -----------------------------
    # Consistency with Case Facts (0–100)
    # -----------------------------
    def _calculate_consistency(
        self, case_text: str, prosecutor_text: str, defense_text: str
    ) -> float:
        case_tokens = self._tokenize(case_text)
        pros_tokens = self._tokenize(prosecutor_text)
        def_tokens = self._tokenize(defense_text)

        overlap_score = min(len(case_tokens & pros_tokens) * 4, 50)
        defense_overlap = min(len(case_tokens & def_tokens) * 2, 20)

        numeric_case = {w for w in case_text.split() if w.isdigit()}
        numeric_args = {
            w for w in (prosecutor_text + " " + defense_text).split() if w.isdigit()
        }
        numeric_score = 20 if numeric_case & numeric_args else 0

        contradiction_keywords = [
            "wrong location", "different time",
            "incorrect facts"
        ]
        penalty = 15 if any(k in defense_text.lower() for k in contradiction_keywords) else 0

        consistency = overlap_score + defense_overlap + numeric_score - penalty
        return round(min(max(consistency, 0), 100), 2)

    # -----------------------------
    # Judge Deliberation (LLM explanation only)
    # -----------------------------
    def deliberate(
        self, verdict: str, case: str, prosecutor_argument: str,
        defense_argument: str, offence: str
    ) -> str:
        law_info = self._validate_law(offence)
        max_fine = law_info.get("max_fine", 5000)

        if not self.llm:
            return (
                f"The court, after examining the record, upholds the verdict: {verdict}. "
                f"The imposed fine shall not exceed PKR {max_fine}."
            )

        prompt = f"""
You are a Pakistani traffic court judge.

Rules:
- Verdict is FINAL
- Formal judicial tone
- Max 150 words
- Fine must not exceed PKR {max_fine}

Verdict: {verdict}
Case: {case}
Prosecutor: {prosecutor_argument[:300]}
Defense: {defense_argument[:300]}

Provide legal reasoning and lawful punishment from Pakistani traffic law.
"""
        return self.llm(prompt)

    # -----------------------------
    # Full Evaluation Pipeline
    # -----------------------------
    def evaluate(
        self,
        debate_id: str,
        case: str,
        case_id: str,  # Manual case_id
        offence: str,
        prosecutor_argument: str,
        defense_argument: str,
        evidence_list: List[Dict],
        hearing_log: List[Dict]
    ) -> JudgementModel:

        evidence_score = self._calculate_evidence_strength(evidence_list)
        legal_score = self._calculate_legal_application(prosecutor_argument, evidence_list)
        defense_eff_score = self._calculate_defense_effectiveness(defense_argument)
        consistency_score = self._calculate_consistency(case, prosecutor_argument, defense_argument)

        # Aggregate scores
        prosecution_score = round((evidence_score * 0.6 + legal_score * 0.4), 2)
        defense_score = round(defense_eff_score, 2)

        final_score = (
            evidence_score * 0.35 +
            legal_score * 0.30 +
            consistency_score * 0.20 -
            defense_eff_score * 0.25
        )

        # Verdict logic
        if final_score >= 65 and prosecution_score > defense_score:
            verdict = "Violation Confirmed"
        elif final_score <= 45 and defense_score > prosecution_score:
            verdict = "Violation Not Confirmed"
        else:
            verdict = "Benefit of Doubt Granted"

        reasoning = self.deliberate(verdict, case, prosecutor_argument, defense_argument, offence)

        rubric_scores = {
            "evidence_strength": evidence_score,
            "legal_application": legal_score,
            "defense_effectiveness": defense_eff_score,
            "consistency": consistency_score,
            "final_score": round(final_score, 2)
        }

        log_judgement(debate_id=debate_id, scores=rubric_scores, verdict=verdict)

        return JudgementModel(
            judgement_id=str(uuid.uuid4()),
            case_id=case_id,  # Manual case_id
            verdict=verdict,
            prosecution_score=prosecution_score,
            defense_score=defense_score,
            rubric_scores=rubric_scores,
            reasoning=reasoning,
            case_facts=case,
            evidence_considered=evidence_list,
            hearing_log=hearing_log
        )

