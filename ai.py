"""
ai.py
-----
Wraps Google's Gemini API to turn a student profile + a list of
universities into a readable recommendation, and to compare two
universities against a profile.

Requires the `google-genai` package and a valid Gemini API key
(get one at https://aistudio.google.com/apikey).
"""

from typing import List

from google import genai

from utils import StudentProfile, University

MODEL_NAME = "gemini-2.5-flash"


class GeminiAIError(Exception):
    """Raised when the Gemini API call fails for any reason."""


class GeminiAI:
    """Small helper class around the Gemini generative model."""

    def __init__(self, api_key: str):
        if not api_key:
            raise GeminiAIError("No Gemini API key configured. Add one in Settings.")
        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as exc:  # noqa: BLE001 - surface any SDK init error
            raise GeminiAIError(f"Failed to initialize Gemini client: {exc}")

    # -- internal helper ----------------------------------------------------

    def _generate(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(model=MODEL_NAME, contents=prompt)
            text = (response.text or "").strip()
            if not text:
                raise GeminiAIError("Gemini returned an empty response. Please try again.")
            return text
        except GeminiAIError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GeminiAIError(f"Gemini request failed: {exc}")

    # -- public API -----------------------------------------------------------

    def generate_recommendation(self, profile: StudentProfile, universities: List[University]) -> str:
        """Analyze the student's profile (optionally alongside a shortlist
        of searched universities) and return AI-generated guidance."""

        uni_list_text = "None searched yet." if not universities else "\n".join(
            f"- {u.name} ({u.country})" for u in universities[:15]
        )

        prompt = f"""
You are a friendly, knowledgeable university admissions counselor.

Here is the student's profile:
- Full Name: {profile.full_name}
- GPA: {profile.gpa} (out of 4.0)
- Intended Major: {profile.major}
- Preferred Country: {profile.country}
- Degree Level: {profile.degree_level}
- Budget: {profile.budget}
- Interests: {profile.interests or 'Not specified'}

Universities the student has searched for (optional shortlist, may be empty):
{uni_list_text}

Write a clear, well-organized recommendation using the following section
headings exactly (as plain text headings, no markdown symbols like # or **):

1. Best University Recommendations
   List 3-5 specific universities (use the shortlist above if relevant and
   suitable, otherwise suggest well-known real universities that fit the
   profile) with one line each on why they fit.

2. Why They Are Suitable
   Briefly connect the student's GPA, major, budget and interests to the
   recommendations above.

3. Admission Tips
   3-5 practical, actionable tips for this student's profile.

4. Skills To Improve
   3-5 concrete skills relevant to their major/interests.

5. Suggested Certifications
   2-4 certifications or courses that would strengthen their application.

6. Career Advice
   A short, encouraging paragraph about career paths related to their major.

Keep the tone professional but encouraging. Keep the whole response under
500 words.
"""
        return self._generate(prompt)

    def compare_universities(self, profile: StudentProfile, uni_a: University, uni_b: University) -> str:
        """Ask Gemini to compare two universities in the context of the
        student's profile."""

        prompt = f"""
You are a university admissions counselor helping a student choose between
two universities.

Student profile:
- Major: {profile.major}
- Degree Level: {profile.degree_level}
- Budget: {profile.budget}
- Interests: {profile.interests or 'Not specified'}

University A: {uni_a.name} ({uni_a.country})
University B: {uni_b.name} ({uni_b.country})

Compare the two universities using the following section headings exactly
(as plain text, no markdown symbols like # or **):

Reputation
Academics
Career Opportunities
Student Life
Final Recommendation

In "Final Recommendation", clearly state which university better fits THIS
student's profile and budget, with 2-3 sentences of reasoning. If you are
not fully certain about specific real-world details of a university, give
a reasonable general assessment rather than inventing precise statistics.

Keep the entire response under 350 words.
"""
        return self._generate(prompt)
