"""
streamlit_app.py
-----------------
Streamlit version of AI College Finder.

This file replaces gui.py + main.py from the CustomTkinter desktop build.
api.py, ai.py, pdf_export.py, and utils.py are reused UNCHANGED — only the
UI layer needed to be rewritten, since Streamlit's rerun-based model works
very differently from CustomTkinter's event-driven windows.

Run with:
    streamlit run streamlit_app.py

Then deploy for free (shareable link) via https://share.streamlit.io
"""
import os
import tempfile
import streamlit as st

from ai import GeminiAI, GeminiAIError
from api import UniversityAPI, UniversityAPIError
from pdf_export import PDFReportGenerator
from utils import (
    BUDGET_LEVELS,
    COMMON_COUNTRIES,
    DEGREE_LEVELS,
    AppState,
    StudentProfile,
    University,
    validate_profile,
    validate_search_query,
)

# ---------------------------------------------------------------------------
# Page config + light custom styling (Streamlit's dark theme handles most of
# the "professional dark SaaS" look already; this just polishes spacing).
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI College Finder",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1.2rem;
        }
        .uni-card {
            background-color: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 14px 18px;
            margin-bottom: 10px;
        }
        .uni-card h4 { margin: 0 0 4px 0; }
        .uni-card p { margin: 0; color: rgba(255,255,255,0.6); font-size: 0.85rem; }
        section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.08); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state initialization (Streamlit's equivalent of AppState in gui.py)
# ---------------------------------------------------------------------------

def init_state():
    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState()
    if "gemini_client" not in st.session_state:
        st.session_state.gemini_client = None


def get_gemini() -> GeminiAI | None:
    """Lazily build the Gemini client, same pattern as gui.py's ensure_gemini()."""
    if st.session_state.gemini_client is not None:
        return st.session_state.gemini_client
    api_key = st.session_state.get("user_api_key", "")
    if not api_key:
        st.warning("⚠️ No Gemini API key configured. Add one on the **Settings** page first.")
        return None
    try:
        st.session_state.gemini_client = GeminiAI(api_key)
        return st.session_state.gemini_client
    except GeminiAIError as exc:
        st.error(str(exc))
        return None


init_state()
state: AppState = st.session_state.app_state


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.markdown("## 🎓 AI College Finder")
st.sidebar.caption("Smart university guidance")

PAGES = [
    "👤 Student Profile",
    "🔎 University Search",
    "✨ AI Recommendation",
    "⚖️ Compare Universities",
    "★ Favorites",
    "📄 Export Report",
    "⚙️ Settings",
]
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption("v1.0 • Streamlit Build")


# ---------------------------------------------------------------------------
# Reusable widget: university card
# ---------------------------------------------------------------------------

def render_university_card(uni: University, key_prefix: str, show_favorite_btn=False,
                            show_remove_btn=False):
    col1, col2 = st.columns([4, 1.6])
    with col1:
        location = uni.country + (f" • {uni.state_province}" if uni.state_province else "")
        st.markdown(
            f"""<div class="uni-card"><h4>{uni.name}</h4><p>{location}</p></div>""",
            unsafe_allow_html=True,
        )
    with col2:
        if uni.website:
            st.link_button("🌐 Website", uni.website, use_container_width=True)
        if show_favorite_btn:
            already = any(f.name == uni.name and f.country == uni.country for f in state.favorites)
            if st.button("★ Saved" if already else "☆ Add to Favorites",
                         key=f"{key_prefix}_fav", disabled=already, use_container_width=True):
                state.favorites.append(uni)
                st.rerun()
        if show_remove_btn:
            if st.button("✕ Remove", key=f"{key_prefix}_remove", use_container_width=True):
                state.favorites[:] = [
                    f for f in state.favorites if not (f.name == uni.name and f.country == uni.country)
                ]
                st.rerun()


# ---------------------------------------------------------------------------
# Page: Student Profile
# ---------------------------------------------------------------------------

if page == "👤 Student Profile":
    st.title("Student Profile")
    st.caption("Tell us about yourself so the AI can tailor its recommendations.")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", value=state.profile.full_name, placeholder="e.g. Ahmed Khan")
            major = st.text_input("Intended Major", value=state.profile.major, placeholder="e.g. Electrical Engineering")
            degree_level = st.selectbox("Degree Level", DEGREE_LEVELS,
                                         index=DEGREE_LEVELS.index(state.profile.degree_level)
                                         if state.profile.degree_level in DEGREE_LEVELS else 0)
        with col2:
            gpa = st.text_input("GPA (out of 4.0)", value=state.profile.gpa, placeholder="e.g. 3.6")
            country = st.selectbox("Preferred Country", COMMON_COUNTRIES,
                                    index=COMMON_COUNTRIES.index(state.profile.country)
                                    if state.profile.country in COMMON_COUNTRIES else 0)
            budget = st.selectbox("Budget", BUDGET_LEVELS,
                                   index=BUDGET_LEVELS.index(state.profile.budget)
                                   if state.profile.budget in BUDGET_LEVELS else 1)

        interests = st.text_area("Interests (comma separated)", value=state.profile.interests,
                                  placeholder="e.g. robotics, AI, chess")

        submitted = st.form_submit_button("Save Profile", type="primary")
        if submitted:
            profile = StudentProfile(
                full_name=full_name, gpa=gpa, major=major, country=country,
                degree_level=degree_level, budget=budget, interests=interests,
            )
            is_valid, message = validate_profile(profile)
            if not is_valid:
                st.warning(message)
            else:
                state.profile = profile


# ---------------------------------------------------------------------------
# Page: University Search
# ---------------------------------------------------------------------------

elif page == "🔎 University Search":
    st.title("University Search")
    st.caption("Search the global university directory by country and/or name.")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        country_q = st.text_input("Country", placeholder="e.g. Pakistan")
    with col2:
        name_q = st.text_input("University Name (optional)", placeholder="e.g. Institute of Technology")
    with col3:
        st.write("")
        st.write("")
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    if search_clicked:
        is_valid, message = validate_search_query(country_q, name_q)
        if not is_valid:
            st.warning(message)
        else:
            with st.spinner("Searching universities..."):
                try:
                    results = UniversityAPI.search(country=country_q, name=name_q)
                    state.search_results = results
                except UniversityAPIError as exc:
                    st.error(str(exc))
                    state.search_results = []

    if state.search_results:
        st.success(f"Found {len(state.search_results)} universit{'y' if len(state.search_results) == 1 else 'ies'}.")
        for i, uni in enumerate(state.search_results):
            render_university_card(uni, key_prefix=f"search_{i}", show_favorite_btn=True)
    else:
        st.info("Search above to see universities here.")


# ---------------------------------------------------------------------------
# Page: AI Recommendation
# ---------------------------------------------------------------------------

elif page == "✨ AI Recommendation":
    st.title("AI Recommendation")
    st.caption("Generate a personalized recommendation based on your saved profile.")

    if st.button("✨ Generate Recommendation", type="primary"):
        is_valid, message = validate_profile(state.profile)
        if not is_valid:
            st.warning("Please complete and save your Student Profile first.")
        else:
            gemini = get_gemini()
            if gemini:
                with st.spinner("Analyzing your profile..."):
                    try:
                        text = gemini.generate_recommendation(state.profile, state.search_results)
                        state.last_recommendation = text
                    except GeminiAIError as exc:
                        st.error(str(exc))

    if state.last_recommendation:
        st.markdown("---")
        st.markdown(state.last_recommendation)
    else:
        st.info("Your AI-generated recommendation will appear here.")


# ---------------------------------------------------------------------------
# Page: Compare Universities
# ---------------------------------------------------------------------------

elif page == "⚖️ Compare Universities":
    st.title("Compare Universities")
    st.caption("Pick two universities from your search results or favorites to compare.")

    pool = state.favorites + state.search_results
    seen, unique = set(), []
    for u in pool:
        key = (u.name, u.country)
        if key not in seen:
            seen.add(key)
            unique.append(u)

    if len(unique) < 2:
        st.info("Search for or favorite at least two universities first.")
    else:
        labels = [u.display_name for u in unique]
        choice_map = {u.display_name: u for u in unique}

        col1, col2 = st.columns(2)
        with col1:
            label_a = st.selectbox("University A", labels, index=0)
        with col2:
            label_b = st.selectbox("University B", labels, index=1 if len(labels) > 1 else 0)

        if st.button("⚖️ Compare", type="primary"):
            if label_a == label_b:
                st.warning("Please select two different universities.")
            elif not state.profile.is_complete():
                st.warning("Please complete and save your Student Profile first.")
            else:
                gemini = get_gemini()
                if gemini:
                    with st.spinner("Comparing universities with AI..."):
                        try:
                            text = gemini.compare_universities(state.profile, choice_map[label_a], choice_map[label_b])
                            state.last_comparison = text
                        except GeminiAIError as exc:
                            st.error(str(exc))

    if state.last_comparison:
        st.markdown("---")
        st.markdown(state.last_comparison)
    else:
        st.info("Your AI-generated comparison will appear here.")


# ---------------------------------------------------------------------------
# Page: Favorites
# ---------------------------------------------------------------------------

elif page == "★ Favorites":
    st.title("Favorites")
    st.caption("Universities you've saved for comparison and your final report.")

    if not state.favorites:
        st.info("No favorites yet. Add some from the Search page.")
    else:
        for i, uni in enumerate(state.favorites):
            render_university_card(uni, key_prefix=f"fav_{i}", show_remove_btn=True)


# ---------------------------------------------------------------------------
# Page: Export Report
# ---------------------------------------------------------------------------

elif page == "📄 Export Report":
    st.title("Export Report")
    st.caption("Generate a professional PDF report of your profile, favorites, and AI insights.")

    st.markdown("""
    **Your report will include:**
    - ✓ Student profile summary
    - ✓ Favorite universities
    - ✓ AI-generated recommendation (if generated)
    - ✓ University comparison (if generated)
    """)

    if not state.profile.is_complete():
        st.warning("Please complete and save your Student Profile first.")
    else:
        if st.button("📄 Generate PDF Report", type="primary"):
            try:
                output_path = os.path.join(tempfile.gettempdir(), "college_report.pdf")
                generator = PDFReportGenerator()
                generator.generate(output_path, state)
                with open(output_path, "rb") as f:
                    pdf_bytes = f.read()
                st.session_state["pdf_bytes"] = pdf_bytes
                st.success("Report generated! Click below to download.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not generate the PDF report: {exc}")

        if "pdf_bytes" in st.session_state:
            file_name = f"{state.profile.full_name.replace(' ', '_')}_College_Report.pdf"
            st.download_button(
                "⬇️ Download PDF Report", data=st.session_state["pdf_bytes"],
                file_name=file_name, mime="application/pdf", type="primary",
            )


# ---------------------------------------------------------------------------
# Page: Settings
# ---------------------------------------------------------------------------

elif page == "⚙️ Settings":
    st.title("Settings")
    st.caption("Configure your Gemini API key. Get a free key at "
               "[aistudio.google.com/apikey](https://aistudio.google.com/apikey)")

    current_key = st.session_state.get("user_api_key", "")
    key_input = st.text_input("Gemini API Key", value=current_key, type="password")
    st.caption("🔒 Your key is kept only in your current browser session — it is "
               "never written to shared disk and is not visible to other visitors. "
               "You'll need to re-enter it if you refresh or come back later.")

    if st.button("Save API Key", type="primary"):
        if not key_input:
            st.warning("Please enter a valid Gemini API key.")
        else:
            st.session_state.user_api_key = key_input
            st.session_state.gemini_client = None  # force re-init with the new key
            st.success("✓ API key saved for this session.")

    st.markdown("---")
    st.caption(
        "💡 On Streamlit Community Cloud, prefer using **Secrets** "
        "(Settings → Secrets) instead of typing your key here, so it "
        "isn't stored in a local file on the server."
    )
