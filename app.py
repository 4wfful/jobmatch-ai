import os
import json
import hashlib
import streamlit as st
from pypdf import PdfReader
from google import genai


st.set_page_config(
    page_title="JobMatch AI",
    page_icon="💼",
    layout="wide"
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def clean_json_response(text):
    """Remove markdown code fences if Gemini includes them."""

    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    return text


def calculate_match_score(requirements):
    """
    Calculate overall match score.

    matched = 100%
    partial = 50%
    missing = 0%

    Required requirements have twice the weight
    of preferred requirements.
    """

    total_weight = 0
    earned_weight = 0

    for requirement in requirements:

        importance = requirement.get(
            "importance",
            "preferred"
        )

        status = requirement.get(
            "status",
            "missing"
        )

        weight = 2 if importance == "required" else 1

        total_weight += weight

        if status == "matched":

            earned_weight += weight

        elif status == "partial":

            earned_weight += weight * 0.5

    if total_weight == 0:
        return 0

    return round(
        (earned_weight / total_weight) * 100
    )


def calculate_category_scores(requirements):
    """Calculate match score for each category."""

    categories = {}

    for requirement in requirements:

        category = requirement.get(
            "category",
            "other"
        )

        importance = requirement.get(
            "importance",
            "preferred"
        )

        status = requirement.get(
            "status",
            "missing"
        )

        weight = 2 if importance == "required" else 1

        if category not in categories:

            categories[category] = {
                "total": 0,
                "earned": 0
            }

        categories[category]["total"] += weight

        if status == "matched":

            categories[category]["earned"] += weight

        elif status == "partial":

            categories[category]["earned"] += weight * 0.5

    scores = {}

    for category, values in categories.items():

        if values["total"] == 0:

            scores[category] = 0

        else:

            scores[category] = round(
                (
                    values["earned"]
                    / values["total"]
                ) * 100
            )

    return scores


def count_statuses(requirements):

    counts = {
        "matched": 0,
        "partial": 0,
        "missing": 0
    }

    for requirement in requirements:

        status = requirement.get(
            "status",
            "missing"
        )

        if status in counts:

            counts[status] += 1

    return counts


def create_cache_key(cv_text, job_description):
    """
    Create a unique identifier for the CV + job description.
    """

    content = (
        cv_text
        + "|||"
        + job_description
    )

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


# =========================================================
# INTERFACE
# =========================================================

st.title("💼 JobMatch AI")

st.subheader(
    "AI-powered job matching and career analysis"
)

st.write(
    "Upload your CV and paste a job description "
    "to analyze how well they match."
)

st.divider()


col1, col2 = st.columns(2)


with col1:

    st.subheader("Your CV")

    cv_file = st.file_uploader(
        "Upload your CV in PDF format",
        type=["pdf"]
    )


with col2:

    st.subheader("Job description")

    job_description = st.text_area(
        "Paste the job description here",
        height=300,
        placeholder=(
            "Paste the complete job description..."
        )
    )


st.divider()


# =========================================================
# ANALYSIS
# =========================================================

if st.button(
    "🔍 Analyze match",
    type="primary"
):

    if cv_file is None:

        st.warning(
            "Please upload your CV."
        )

        st.stop()


    if not job_description.strip():

        st.warning(
            "Please paste a job description."
        )

        st.stop()


    # =====================================================
    # EXTRACT CV TEXT
    # =====================================================

    reader = PdfReader(cv_file)

    cv_text = ""

    for page in reader.pages:

        text = page.extract_text()

        if text:

            cv_text += text + "\n"


    if not cv_text.strip():

        st.error(
            "We couldn't extract text from this PDF. "
            "Please make sure your CV contains selectable text."
        )

        st.stop()


    # =====================================================
    # CACHE KEY
    # =====================================================

    cache_key = create_cache_key(
        cv_text,
        job_description
    )


    # =====================================================
    # CHECK CACHE
    # =====================================================

    if (
        "analysis_cache" in st.session_state
        and cache_key in st.session_state.analysis_cache
    ):

        analysis = (
            st.session_state.analysis_cache[
                cache_key
            ]
        )

        st.info(
            "Using previously generated analysis "
            "to avoid an additional API request."
        )


    else:

        # =================================================
        # GEMINI CLIENT
        # =================================================

        api_key = os.environ.get(
            "GEMINI_API_KEY"
        )


        if not api_key:

            st.error(
                "GEMINI_API_KEY was not found."
            )

            st.stop()


        client = genai.Client(
            api_key=api_key
        )


        # =================================================
        # SINGLE GEMINI REQUEST
        # =================================================

        analysis_prompt = f"""
You are a recruitment analysis engine.

Analyze a candidate's CV against a job description.

Your task has two parts:

1. Extract the important candidate requirements from
the job description.

2. Compare each requirement against the candidate's CV.

IMPORTANT:

Only use evidence explicitly present in the CV.

Do not assume that the candidate has a skill simply
because it would be useful for the role.

Do not treat similar but different experiences as exact
matches.

For every requirement classify the candidate as:

- matched
- partial
- missing

Definitions:

MATCHED:
The CV provides clear evidence that the candidate
meets the requirement.

PARTIAL:
The CV provides related or transferable evidence,
but does not fully demonstrate the requirement.

MISSING:
The CV provides no meaningful evidence for
the requirement.

JOB DESCRIPTION:

{job_description}

CANDIDATE CV:

{cv_text}

Return ONLY valid JSON using exactly this structure:

{{
  "requirements": [
    {{
      "requirement": "string",
      "category": "skills",
      "importance": "required",
      "status": "matched",
      "evidence": "string",
      "reason": "string"
    }}
  ],
  "recommendations": [
    "string"
  ]
}}

Allowed categories:

- skills
- experience
- education
- languages
- tools
- availability
- location
- other

Allowed importance values:

- required
- preferred

Rules:

1. Extract concrete candidate requirements.
2. Do not invent requirements.
3. Avoid duplicate requirements.
4. Keep requirements concise.
5. Use "availability" for work schedule requirements.
6. Use "location" for geographic or timezone requirements.
7. Use "skills" for professional abilities.
8. Use "experience" for previous work experience.
9. Use "education" for degrees or academic requirements.
10. Use "languages" for language requirements.
11. Use "tools" for software, platforms, or technologies.
12. Keep the original requirement meaning when evaluating it.
13. Evidence must come directly from the CV.
14. If evidence is absent, use "missing".
15. Use "partial" for relevant transferable evidence.
16. Provide up to 5 practical recommendations.
17. Do not calculate an overall percentage.
18. Do not invent a probability of being hired.
"""


        with st.spinner(
            "Analyzing your CV and job description..."
        ):

            try:

                interaction = client.interactions.create(
                    model="gemini-3.8-flash",
                    input=analysis_prompt
                )

                response_text = clean_json_response(
                    interaction.output_text
                )

                analysis = json.loads(
                    response_text
                )


            except json.JSONDecodeError:

                st.error(
                    "Gemini returned an invalid JSON format."
                )

                st.stop()


            except Exception as e:

                st.error(
                    f"An error occurred while analyzing "
                    f"the CV: {e}"
                )

                st.stop()


        # =================================================
        # SAVE TO CACHE
        # =================================================

        if "analysis_cache" not in st.session_state:

            st.session_state.analysis_cache = {}


        st.session_state.analysis_cache[
            cache_key
        ] = analysis


    # =====================================================
    # GET REQUIREMENTS
    # =====================================================

    requirements = analysis.get(
        "requirements",
        []
    )


    if not requirements:

        st.error(
            "No job requirements could be identified."
        )

        st.stop()


    # =====================================================
    # CALCULATE METRICS WITH PYTHON
    # =====================================================

    overall_score = calculate_match_score(
        requirements
    )


    category_scores = calculate_category_scores(
        requirements
    )


    status_counts = count_statuses(
        requirements
    )


    # =====================================================
    # RESULTS
    # =====================================================

    st.success(
        "Analysis completed!"
    )

    st.divider()


    # =====================================================
    # MATCH OVERVIEW
    # =====================================================

    st.subheader(
        "🎯 Match overview"
    )


    metric1, metric2, metric3, metric4 = (
        st.columns(4)
    )


    with metric1:

        st.metric(
            "Estimated match",
            f"{overall_score}%"
        )


    with metric2:

        st.metric(
            "Matched",
            status_counts["matched"]
        )


    with metric3:

        st.metric(
            "Partial",
            status_counts["partial"]
        )


    with metric4:

        st.metric(
            "Missing",
            status_counts["missing"]
        )


    st.caption(
        "The estimated match represents alignment "
        "with the requirements identified in the job "
        "description. It is not a probability of being hired."
    )


    # =====================================================
    # CATEGORY SCORES
    # =====================================================

    if category_scores:

        st.divider()

        st.subheader(
            "📊 Match by category"
        )


        category_columns = st.columns(
            len(category_scores)
        )


        for column, (
            category,
            score
        ) in zip(
            category_columns,
            category_scores.items()
        ):

            with column:

                st.metric(
                    category.title(),
                    f"{score}%"
                )


    # =====================================================
    # REQUIREMENT BREAKDOWN
    # =====================================================

    st.divider()

    st.subheader(
        "📋 Requirement breakdown"
    )


    for item in requirements:

        requirement = item.get(
            "requirement",
            "Unknown requirement"
        )

        status = item.get(
            "status",
            "missing"
        )

        importance = item.get(
            "importance",
            "preferred"
        )

        category = item.get(
            "category",
            "other"
        )

        evidence = item.get(
            "evidence",
            ""
        )

        reason = item.get(
            "reason",
            ""
        )


        if status == "matched":

            icon = "✅"

        elif status == "partial":

            icon = "🟡"

        else:

            icon = "❌"


        with st.expander(
            f"{icon} {requirement}"
        ):

            st.write(
                f"**Category:** {category}"
            )

            st.write(
                f"**Importance:** {importance}"
            )

            st.write(
                f"**Status:** {status}"
            )

            if evidence:

                st.write(
                    f"**CV evidence:** {evidence}"
                )

            if reason:

                st.write(
                    f"**Analysis:** {reason}"
                )


    # =====================================================
    # RECOMMENDATIONS
    # =====================================================

    recommendations = analysis.get(
        "recommendations",
        []
    )


    if recommendations:

        st.divider()

        st.subheader(
            "🚀 Recommendations"
        )


        for recommendation in recommendations:

            st.write(
                f"• {recommendation}"
            )