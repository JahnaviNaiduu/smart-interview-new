import json
import logging
from datetime import datetime, timezone
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)
_client = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def rank_slots(slots: list[dict], candidate_timezone: str, panelist_interview_counts: dict) -> list[dict]:
    """Use Llama via Groq to rank slots. Falls back to chronological order if AI fails."""
    if not slots:
        return slots

    slot_data = [
        {
            "slot_id": str(s.get("id", i)),
            "start_utc": s["start"].isoformat() if isinstance(s["start"], datetime) else s["start"],
            "end_utc": s["end"].isoformat() if isinstance(s["end"], datetime) else s["end"],
        }
        for i, s in enumerate(slots)
    ]

    prompt = f"""You are a scheduling assistant. Rank these interview time slots from best to worst.

Candidate timezone: {candidate_timezone}

Slots (times in UTC ISO format):
{json.dumps(slot_data, indent=2)}

Panelist interview load (interviews already scheduled today per panelist):
{json.dumps(panelist_interview_counts)}

Ranking criteria in order of priority:
1. The slot must be a reasonable hour for the CANDIDATE (9 AM - 6 PM in {candidate_timezone})
2. Morning slots (9 AM - 12 PM) preferred over afternoon
3. Prefer panelists with lower interview load today
4. Avoid Monday before 10 AM and Friday after 4 PM
5. Mid-week (Tue, Wed, Thu) preferred

Return ONLY a valid JSON array. No markdown, no explanation, no extra text.
Format:
[
  {{"slot_index": 0, "rank": 1, "score": 0.95, "reasoning": "Morning slot, good timezone fit, low panelist load"}},
  ...
]
Every slot must appear in the output with a rank."""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="groq/compound-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a scheduling assistant. Always respond with valid JSON only. No markdown formatting.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        # Truncate to last complete JSON object if needed
        last_bracket = raw.rfind("]")
        if last_bracket != -1:
            raw = raw[:last_bracket + 1]
        ranked = json.loads(raw)

        for item in ranked:
            idx = item["slot_index"]
            if idx < len(slots):
                slots[idx]["ai_rank"] = item["rank"]
                slots[idx]["ai_score"] = item["score"]
                slots[idx]["ai_reasoning"] = item["reasoning"]

        slots.sort(key=lambda x: x.get("ai_rank", 999))
        return slots

    except Exception as e:
        logger.warning(f"AI ranking failed, using chronological order: {e}")
        for i, slot in enumerate(sorted(slots, key=lambda x: x["start"])):
            slot["ai_rank"] = i + 1
            slot["ai_score"] = None
            slot["ai_reasoning"] = None
        return slots


def generate_invite_email(
    candidate_name: str,
    round_type: str,
    job_title: str,
    recruiter_name: str,
    company_name: str = "our company",
) -> str:
    """Generate personalized interview invitation email body."""
    round_descriptions = {
        "screening": "initial screening",
        "technical": "technical",
        "managerial": "managerial",
        "hr": "HR",
    }
    round_label = round_descriptions.get(round_type, round_type)

    prompt = f"""Write a professional, warm interview invitation email body.

Details:
- Candidate name: {candidate_name}
- Interview round: {round_label} interview
- Job title: {job_title}
- Recruiter name: {recruiter_name}
- Company: {company_name}

Requirements:
- Be warm but professional
- Mention the round type naturally
- Tell the candidate to click the link below to pick their preferred time slot
- Keep it under 150 words
- No excessive corporate jargon
- Do NOT include a subject line
- Do NOT include a signature — that will be added separately
- Start directly with "Hi {candidate_name},"

Return ONLY the email body text. No JSON, no markdown."""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="groq/compound-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You write professional, concise HR emails. Return only the email body.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"AI email generation failed, using template: {e}")
        return (
            f"Hi {candidate_name},\n\n"
            f"We'd love to invite you for a {round_label} interview for the {job_title} position at {company_name}. "
            f"Please click the link below to select your preferred time slot.\n\n"
            f"Looking forward to speaking with you!"
        )
