import base64
import streamlit as st

def apply_premium_styling():
    """
    Injects custom CSS for a vibrant, modern LIGHT theme.
    Warm gradients, soft shadows, and clean typography.
    """
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        /* ── Base Reset ────────────────────────────────────── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }
        
        /* ── Main Background ───────────────────────────────── */
        .stApp {
            background: linear-gradient(135deg, #f8f0ff 0%, #eef2ff 40%, #f0fdfa 100%) !important;
        }

        /* ── Sidebar ───────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #6d28d9 0%, #7c3aed 50%, #8b5cf6 100%) !important;
            color: white !important;
        }
        section[data-testid="stSidebar"] * {
            color: white !important;
        }
        section[data-testid="stSidebar"] .stMarkdown p {
            color: rgba(255,255,255,0.85) !important;
        }

        /* ── Header ────────────────────────────────────────── */
        header {
            background-color: transparent !important;
        }
        
        /* ── Hero Title ────────────────────────────────────── */
        .hero-title {
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #6d28d9, #2563eb, #0d9488);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0;
            letter-spacing: -0.5px;
        }
        .hero-subtitle {
            text-align: center;
            color: #64748b;
            font-size: 1.05rem;
            margin-top: 0.2rem;
            font-weight: 400;
        }

        /* ── Buttons ───────────────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #7c3aed, #6d28d9) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.5rem !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 2px 8px rgba(109, 40, 217, 0.25) !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(109, 40, 217, 0.35) !important;
        }

        /* ── Glassmorphic Cards ────────────────────────────── */
        .glass-card {
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(203, 213, 225, 0.8);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 0.75rem 0;
            box-shadow: 0 10px 34px rgba(15, 23, 42, 0.08);
        }
        
        /* ── Metric Cards ──────────────────────────────────── */
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.75);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(109, 40, 217, 0.12);
            border-radius: 14px;
            padding: 1rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        }

        /* ── Dataframes ────────────────────────────────────── */
        .dataframe {
            background-color: white !important;
            border-collapse: separate !important;
            border-spacing: 0;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e2e8f0 !important;
        }
        .dataframe th {
            background: linear-gradient(135deg, #ede9fe, #e0e7ff) !important;
            color: #4c1d95 !important;
            font-weight: 600;
            border-bottom: 2px solid #c4b5fd !important;
        }
        .dataframe td {
            color: #334155 !important;
            border-bottom: 1px solid #f1f5f9 !important;
        }

        /* ── File Uploader ─────────────────────────────────── */
        section[data-testid="stSidebar"] .stFileUploader > div > div {
            background: rgba(255,255,255,0.15) !important;
            border: 2px dashed rgba(255,255,255,0.4) !important;
            border-radius: 12px !important;
            transition: border 0.3s ease;
        }
        section[data-testid="stSidebar"] .stFileUploader > div > div:hover {
            border-color: white !important;
        }

        /* ── Chat Messages ─────────────────────────────────── */
        div[data-testid="stChatMessage"] {
            background: rgba(255,255,255,0.65) !important;
            backdrop-filter: blur(8px);
            border-radius: 14px !important;
            border: 1px solid rgba(0,0,0,0.04) !important;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
            margin-bottom: 0.75rem;
        }

        /* ── Expander ──────────────────────────────────────── */
        .streamlit-expanderHeader {
            background: rgba(255,255,255,0.75) !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }

        div[data-testid="stChatMessage"] .stMarkdown {
            color: #1f2937 !important;
        }

        div[data-testid="stChatMessage"] {
            background: rgba(255,255,255,0.85) !important;
        }

        /* ── Alerts ────────────────────────────────────────── */
        .stAlert {
            border-radius: 12px !important;
        }

        /* ── Agent Step Badges ─────────────────────────────── */
        .agent-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            margin: 2px 4px;
        }
        .badge-schema  { background: #dbeafe; color: #1e40af; }
        .badge-prompt  { background: #fce7f3; color: #9d174d; }
        .badge-code    { background: #d1fae5; color: #065f46; }
        .badge-valid   { background: #fef3c7; color: #92400e; }
        .badge-exec    { background: #ede9fe; color: #5b21b6; }
        .badge-report  { background: #ccfbf1; color: #115e59; }

        /* ── Footer Hide ───────────────────────────────────── */
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)


def render_agent_pipeline():
    """Renders a visual pipeline indicator showing the 6 agents."""
    st.markdown("""
        <div style="text-align:center; margin: 1rem 0;">
            <span class="agent-badge badge-schema">📊 Schema</span>
            <span style="color:#94a3b8;">→</span>
            <span class="agent-badge badge-prompt">✍️ Prompt</span>
            <span style="color:#94a3b8;">→</span>
            <span class="agent-badge badge-code">💻 Code</span>
            <span style="color:#94a3b8;">→</span>
            <span class="agent-badge badge-valid">🛡️ Validate</span>
            <span style="color:#94a3b8;">→</span>
            <span class="agent-badge badge-exec">⚙️ Execute</span>
            <span style="color:#94a3b8;">→</span>
            <span class="agent-badge badge-report">📝 Report</span>
        </div>
    """, unsafe_allow_html=True)


def render_report_card(insights: str, query: str):
    """Renders the insights report inside a premium glass card."""
    st.markdown(f"""
        <div class="glass-card">
            <h3 style="margin-top:0; color:#4c1d95;">✨ Analysis Results</h3>
            <p style="color:#64748b; font-size:0.88rem; margin-bottom:1rem;">Query: <em>"{query}"</em></p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown(insights)


def render_code_block(code: str):
    """Renders the AI generated Python code."""
    with st.expander("💻 View Generated Code", expanded=False):
        st.code(code, language='python')


def render_output_block(output: str):
    """Renders the raw captured stdout."""
    if output and output.strip():
        with st.expander("📤 Raw Execution Output", expanded=False):
            st.code(output, language='text')


def render_chart_block(chart_image_base64: str, caption: str = "Generated Chart"):
    """Renders a chart image from base64 data."""
    if chart_image_base64:
        image_bytes = base64.b64decode(chart_image_base64)
        with st.expander("📈 Generated Chart", expanded=True):
            st.image(image_bytes, caption=caption, use_column_width=True)
