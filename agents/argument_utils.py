def format_evidence(evidence_list):
    if not evidence_list:
        return "No external evidence provided."

    lines = []
    for i, e in enumerate(evidence_list, 1):
        lines.append(
            f"[E{i}] {e['text'][:200]} (confidence={round(e['score'], 2)})"
        )
    return "\n".join(lines)


def build_argument_prompt(role, case, evidence_list, memory_text):
    return f"""
You are a {role} in a traffic violation court.

RULES:
- Max 120 words
- No repetition
- Be precise and legal
- Use bullet points only

CASE:
{case}

EVIDENCE:
{format_evidence(evidence_list)}

PREVIOUS CONTEXT:
{memory_text}

Produce your argument now.
"""


def classify_argument_prompt(argument):
    return f"Classify the legal strength of this argument as STRONG, MODERATE, or WEAK:\n{argument}"


def summarize_prompt(argument):
    return f"Summarize this argument in 2 bullet points:\n{argument}"