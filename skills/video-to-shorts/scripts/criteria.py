"""Short-form selection criteria for candidate generation."""

VIRALITY_CRITERIA = """Short-form propagation signals to prioritize:
1. HOOK MOMENTS: lines that create immediate curiosity within the first seconds.
2. EMOTIONAL PEAKS: surprise, excitement, vulnerability, laughter, anger, or clear stakes.
3. OPINION BOMBS: strong, polarizing, or counter-intuitive claims that invite agreement or disagreement.
4. REVERSALS: moments that overturn a common assumption or reveal that the situation is the opposite of what viewers expect.
5. CONFLICT OR TENSION: a risk, disagreement, challenge, bottleneck, or problem being confronted.
6. QUOTABLE LINES: compact statements that can stand alone as a shareable quote.
7. STORY PEAKS: the payoff, twist, result, or climax of an anecdote or demonstration.
8. PRACTICAL VALUE: concrete advice, explanation, workflow, or insight the viewer can use or understand quickly.

Boundary rules:
- Never cut mid-sentence or mid-thought.
- Each candidate must be complete and self-contained.
- start_time should begin at the first word of a complete sentence or thought.
- end_time should end after the final word of a complete sentence or thought.
- Do not start with fragment phrases if the prior context is needed.
- Do not end with dangling words or incomplete clauses such as "and", "that", "our", "to", "of", or "in fact, that".
"""


def criteria_for_prompt():
    return VIRALITY_CRITERIA
