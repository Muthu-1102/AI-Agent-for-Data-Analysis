import streamlit as st
import pandas as pd
import io
import os

from components import (
    apply_premium_styling, 
    render_agent_pipeline,
    render_report_card, 
    render_code_block,
    render_output_block,
    render_chart_block
)
from api_client import DataAnalystAPI

# ── Page Config (MUST be first Streamlit command) ──────────────────────────
st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply our premium light theme
apply_premium_styling()


def init_session():
    """Initialize session state variables."""
    defaults = {
        "file_id": None,
        "file_name": None,
        "chat_history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def main():
    init_session()

    # ═══════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═══════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown("## 🧠 AI Data Analyst")
        st.markdown("Upload a dataset and ask questions in plain English. Our multi-agent AI pipeline will analyze it for you.")
        
        st.markdown("---")
        
        # File Upload
        uploaded_file = st.file_uploader(
            "📁 Upload your dataset",
            type=['csv'],
            help="Upload a CSV file to begin analysis"
        )
        
        if uploaded_file is not None:
            if st.session_state.file_name != uploaded_file.name:
                with st.spinner("Processing upload..."):
                    try:
                        file_content = uploaded_file.read()
                        uploaded_file.seek(0)
                        
                        file_id = DataAnalystAPI.upload_dataset(
                            io.BytesIO(file_content), uploaded_file.name
                        )
                        
                        st.session_state.file_id = file_id
                        st.session_state.file_name = uploaded_file.name
                        st.session_state.chat_history = []  # reset on new file
                        
                        st.success(f"✅ **{uploaded_file.name}** uploaded!")
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")
            else:
                st.success(f"📄 **{st.session_state.file_name}**")
        
        # Data Preview
        if uploaded_file is not None and st.session_state.file_id:
            st.markdown("---")
            with st.expander("👀 Data Preview", expanded=False):
                try:
                    uploaded_file.seek(0)
                    try:
                        df_preview = pd.read_csv(uploaded_file, nrows=10)
                    except Exception:
                        uploaded_file.seek(0)
                        df_preview = pd.read_csv(uploaded_file, nrows=10, engine='python')
                    st.dataframe(df_preview, use_container_width=True, height=250)
                    st.caption(f"{len(df_preview.columns)} columns detected")
                except Exception:
                    st.warning("Could not render preview.")
        
        st.markdown("---")
        st.markdown("##### 🤖 Agent Pipeline")
        st.markdown("""
        1. **Schema Agent** — Reads structure  
        2. **Prompt Agent** — Enhances query  
        3. **Code Agent** — Writes Python  
        4. **Validation Agent** — Security check  
        5. **Execution Agent** — Runs code  
        6. **Report Agent** — Generates insights
        """)

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN CONTENT
    # ═══════════════════════════════════════════════════════════════════════
    
    # Hero Title
    st.markdown('<h1 class="hero-title">AI Data Analyst</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Ask anything about your data — insights, trends, charts, and more</p>', unsafe_allow_html=True)
    
    # Agent Pipeline Visual
    render_agent_pipeline()
    
    st.markdown("")

    # Gate: require upload first
    if not st.session_state.file_id:
        st.markdown("---")
        # Welcome state
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:2.5rem;">📊</div>
                <h4 style="color:#4c1d95; margin:0.5rem 0;">Insights</h4>
                <p style="color:#64748b; font-size:0.85rem;">Get statistical summaries and key findings from your data</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:2.5rem;">📈</div>
                <h4 style="color:#4c1d95; margin:0.5rem 0;">Visualizations</h4>
                <p style="color:#64748b; font-size:0.85rem;">Generate charts, plots, and visual representations automatically</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:2.5rem;">🔄</div>
                <h4 style="color:#4c1d95; margin:0.5rem 0;">Transformations</h4>
                <p style="color:#64748b; font-size:0.85rem;">Clean, filter, and reshape your data with natural language</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")
        st.info("👈 **Upload a CSV file** from the sidebar to get started!")
        return

    # ───────────────────────────────────────────────────────────────────────
    # Chat History
    # ───────────────────────────────────────────────────────────────────────
    for entry in st.session_state.chat_history:
        with st.chat_message("user", avatar="👤"):
            st.write(entry["query"])
        with st.chat_message("assistant", avatar="🧠"):
            if entry.get("error"):
                st.error(entry["error"])
            else:
                if entry.get("chart_image"):
                    render_chart_block(entry.get("chart_image"))
                render_report_card(entry.get("insights", ""), entry["query"])
                if entry.get("code"):
                    render_code_block(entry["code"])
                if entry.get("output"):
                    render_output_block(entry["output"])

    # ───────────────────────────────────────────────────────────────────────
    # Chat Input
    # ───────────────────────────────────────────────────────────────────────
    query = st.chat_input(
        "Ask a question about your data... (e.g., 'What are the top 5 products by revenue?')"
    )
    
    if query:
        # Show user message
        with st.chat_message("user", avatar="👤"):
            st.write(query)
            
        # Show assistant response
        with st.chat_message("assistant", avatar="🧠"):
            with st.status("🔄 Running multi-agent analysis pipeline...", expanded=True) as status_box:
                st.write("📊 Schema Agent analyzing dataset structure...")
                st.write("✍️ Prompt Agent enhancing your query...")
                st.write("💻 Code Agent generating Python code...")
                st.write("🛡️ Validation Agent checking security...")
                st.write("⚙️ Execution Agent running code...")
                st.write("📝 Report Agent generating insights...")
                
                try:
                    result = DataAnalystAPI.process_query(query, st.session_state.file_id)
                    
                    pipeline_status = result.get("status", "error")
                    insights = result.get("insights_summary", "")
                    code = result.get("generated_code", "")
                    output = result.get("captured_output", "")
                    chart_image = result.get("chart_image_base64")
                    error = result.get("error")
                    
                    if pipeline_status == "completed" and insights:
                        status_box.update(
                            label="✅ Analysis complete!", 
                            state="complete", 
                            expanded=False
                        )
                        if chart_image:
                            render_chart_block(chart_image)
                        render_report_card(insights, query)
                        if code:
                            render_code_block(code)
                        if output:
                            render_output_block(output)
                        
                        # Save to history
                        st.session_state.chat_history.append({
                            "query": query,
                            "insights": insights,
                            "code": code,
                            "output": output,
                            "chart_image": chart_image,
                            "error": None
                        })
                    else:
                        error_msg = error or "Pipeline returned no insights."
                        status_box.update(
                            label="⚠️ Pipeline encountered an issue",
                            state="error",
                            expanded=True
                        )
                        st.error(error_msg)
                        
                        st.session_state.chat_history.append({
                            "query": query,
                            "insights": None,
                            "code": code,
                            "output": output,
                            "error": error_msg
                        })
                        
                except Exception as e:
                    status_box.update(
                        label="❌ Connection failed",
                        state="error", 
                        expanded=True
                    )
                    st.error(f"Could not reach the backend: {str(e)}")
                    st.info("Make sure the FastAPI backend is running on http://localhost:8000")
                    
                    st.session_state.chat_history.append({
                        "query": query,
                        "insights": None,
                        "code": None,
                        "output": None,
                        "error": str(e)
                    })


if __name__ == "__main__":
    main()
