import streamlit as st
import streamlit.components.v1 as components
import asyncio
import os
from state_manager import StateManager

st.set_page_config(page_title="llms.txt Generator", page_icon="📄", layout="centered")
from config_manager import ConfigManager
from extractor import process_single_page
import json
from urllib.parse import urlparse

DEFAULT_PROMPT_TEMPLATE = """You are an expert technical writer specializing in the llms.txt specification.
Generate a standard `llms.txt` body from the JSON Link Tree below for the website: {url}

### CONTEXT CLUES — use these to make smarter grouping decisions:
- **Domain**: {domain}
- **URL path segments** (e.g. `/docs/`, `/api/`, `/blog/`, `/pricing/`) reveal the site's structure — use them to name and group sections accurately.
- **Existing category labels** in the JSON come from the page's own headings and nav landmarks — treat them as strong hints, but merge duplicates and rename vague ones (e.g. "General", "Footer", "Header Navigation") into meaningful section names based on the URLs they contain.

### OUTPUT RULES:
1. **Format**: Strict Markdown only.
2. **Structure**:
   ## [Logical Section Name]
   - [Descriptive Link Title](URL): One concise sentence describing what this page covers.
3. **Grouping**:
   - Merge near-duplicate categories (e.g. "Docs", "Documentation", "documentation" → ## Documentation).
   - Rename structural/layout categories ("General", "Footer", "Header Navigation") to reflect their actual content based on the URLs they contain.
   - Infer missing context from URL path segments when link text is ambiguous.
   - Suggested sections (use only those relevant): Documentation, API Reference, Guides & Tutorials, Blog, Pricing, Use Cases, Integrations, Company, Legal, Support.
4. **No Preamble**: Output ONLY raw Markdown. No intro sentence, no explanation.

Link Tree Data:
"""

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp, .stApp [data-testid="stWidgetLabel"], .stApp p, .stApp li,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        font-family: 'Inter', sans-serif !important;
        color: #fafafa !important;
    }
    .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp summary {
        font-family: 'Inter', sans-serif !important;
    }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    [data-testid="stSidebar"] {display: none;}

    label[data-testid="stWidgetLabel"] p {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: #e4e4e7 !important;
        margin-bottom: 6px !important;
    }

    div.stButton > button {
        border-radius: 6px;
        text-align: center;
        min-width: max-content;
        font-size: 16px;
        padding: 8px 18px;
        font-weight: 500;
    }
            
    stButton {
        max-width: max-content;
            
    }

    /* Nav row flex container */
    #nav-row-container {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
    }
    #nav-row-container > div:has(#nav-row-marker) {
        display: none !important;
    }

    div[data-testid="stCodeBlock"] {
        max-height: 320px !important;
        overflow-y: auto !important;
        background-color: #09090b !important;
    }


    .stCode {    
        height: max-content !important;
        max-height: 200px !important; 
        overflow-y: auto;
    }
            
    pre {
        max-height: 100% !important;
        overflow-y: auto !important;
    }

    /* Wizard layout */
    .app-title {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #fafafa;
        margin-bottom: 0.25rem;
    }
    .app-subtitle {
        font-size: 0.85rem;
        color: #71717a;
        margin-bottom: 2rem;
    }

    /* Step indicator */
    .wizard-nav {
        display: flex;
        align-items: flex-start;
        margin-bottom: 20px;
        gap: 0;
    }
    .wizard-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        min-width: 72px;
    }
    .step-circle {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        border: 1.5px solid #27272a;
        color: #52525b;
        background: transparent;
        transition: all 0.2s;
    }
    .step-circle.active {
        background: #fafafa;
        color: #09090b;
        border-color: #fafafa;
    }
    .step-circle.done {
        background: #1b4623;
        color: #0cd945;
        border-color: #0cd945;
    }
    .step-label {
        font-size: 0.7rem;
        color: #52525b;
        font-weight: 500;
        text-align: center;
    }
    .step-label.active { color: #fafafa; }
    .step-label.done   { color: #71717a; }
    .step-connector {
        width: 64px;
        height: 1.5px;
        background: #27272a;
        margin-top: 15px;
        flex-shrink: 0;
    }
    .step-connector.done { background: #3f3f46; }

    /* Step card — applied to Streamlit's own block container */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        background: #0a0a0a !important;
        padding: 0.25rem 0.5rem !important;
        margin-bottom: 1.25rem !important;
    }
    .step-heading {
        font-size: 1rem;
        font-weight: 600;
        color: #fafafa;
        margin-bottom: 0.15rem;
        letter-spacing: -0.01em;
    }
    .step-desc {
        font-size: 0.82rem;
        color: #71717a;
        margin-bottom: 1.25rem;
    }

    /* Link grid */
    .link-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 0.6rem 1.2rem;
        font-size: 0.75rem;
        padding: 0.4rem 0 0.8rem 0;
    }
    .link-item {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #a1a1aa;
    }
    .link-item a { color: #60a5fa !important; text-decoration: none; }
    .link-item a:hover { text-decoration: underline; }
    .category-title {
        font-size: 0.7rem;
        font-weight: 600;
        margin: 0.8rem 0 0.4rem 0;
        border-bottom: 1px solid #1c1c1e;
        padding-bottom: 4px;
        color: #52525b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .link-scroll {
        max-height: 380px;
        overflow-y: auto;
        padding-right: 6px;
    }

    .st-emotion-cache-zy6yx3 { padding: 20px 60px; }

    /* Reduce top padding so the app is visible without scrolling */
    .stMainBlockContainer, div[data-testid="stMainBlockContainer"] {
        padding-top: 1.5rem !important;
    }
    div[data-testid="stAppViewContainer"] > section > div:first-child {
        padding-top: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# ── State ────────────────────────────────────────────────────────────────────
state_mgr = StateManager()
config_mgr = ConfigManager()

if "wizard_step" not in st.session_state:
    st.session_state.wizard_step = 1

# ── Helpers ──────────────────────────────────────────────────────────────────
def go(step):
    st.session_state.wizard_step = step
    st.rerun()

def step_indicator(current):
    labels = ["Setup", "Extract", "Generate", "Download"]
    html = '<div class="wizard-nav">'
    for i, label in enumerate(labels):
        n = i + 1
        if n < current:
            cc, lc = "step-circle done", "step-label done"
            inner = "✓"
        elif n == current:
            cc, lc = "step-circle active", "step-label active"
            inner = str(n)
        else:
            cc, lc = "step-circle", "step-label"
            inner = str(n)
        html += f'<div class="wizard-step"><div class="{cc}">{inner}</div><div class="{lc}">{label}</div></div>'
        if i < len(labels) - 1:
            conn_class = "step-connector done" if n < current else "step-connector"
            html += f'<div class="{conn_class}"></div>'
    html += '</div>'
    return html

def copy_button(text, key):
    safe = json.dumps(text)
    components.html(f"""
        <button id="cb-{key}" style="
            background:transparent;border:1px solid #3f3f46;border-radius:4px;
            color:#a1a1aa;padding:2px 12px;font-size:0.72rem;font-family:Inter,sans-serif;
            cursor:pointer;line-height:1.6;
        ">Copy</button>
        <script>
        document.getElementById('cb-{key}').addEventListener('click', function() {{
            navigator.clipboard.writeText({safe}).then(() => {{
                this.textContent = 'Copied!';
                setTimeout(() => this.textContent = 'Copy', 1500);
            }});
        }});
        </script>
    """, height=32)

def render_link_tree(link_tree):
    st.markdown('<div class="link-scroll">', unsafe_allow_html=True)
    for category, links in link_tree.items():
        st.markdown(f'<div class="category-title">{category}</div>', unsafe_allow_html=True)
        items = "".join(
            f'<div class="link-item">• <a href="{l["url"]}" target="_blank">{l["text"]}</a></div>'
            for l in links
        )
        st.markdown(f'<div class="link-grid">{items}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="app-title">llms.txt Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Generate a structural map of your domain for AI indexing.</div>', unsafe_allow_html=True)

step = st.session_state.wizard_step

# ── Thank-you screen (outside wizard) ────────────────────────────────────────
if step == 5:
    st.markdown("""
        <div style="text-align:center;padding:3rem 0 1.5rem;">
            <div style="font-size:2rem;margin-bottom:0.75rem;">✓</div>
            <div style="font-size:1.25rem;font-weight:600;color:#fafafa;margin-bottom:0.5rem;">
                Your llms.txt is downloaded.
            </div>
            <div style="font-size:0.85rem;color:#71717a;">
                Thanks for using llms.txt Generator. Come back anytime to index another domain.
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Start Over", key="done_reset"):
        go(1)
    st.stop()

st.markdown(step_indicator(step), unsafe_allow_html=True)

# ── Navigation helper ────────────────────────────────────────────────────────
def nav_row(back_label=None, back_key=None, back_fn=None,
            next_label=None, next_key=None, next_fn=None,
            next_widget=None):
    """Renders Back on the far left, primary action on the far right."""
    with st.container():
        st.markdown('<span id="nav-row-marker" style="display:none"></span>', unsafe_allow_html=True)
        back_clicked = back_label and st.button(back_label, key=back_key)
        if next_widget:
            next_widget()
        else:
            next_clicked = next_label and st.button(next_label, type="primary", key=next_key)
    # Callbacks run outside the flex container so alerts render in normal flow
    if back_clicked:
        back_fn()
    elif next_label and next_clicked:
        next_fn()
    components.html("""
        <script>
        (function() {
            function label() {
                var doc = window.parent.document;
                var marker = doc.getElementById('nav-row-marker');
                if (marker) {
                    var block = marker.closest('[data-testid="stVerticalBlock"]');
                    if (block) block.id = 'nav-row-container';
                }
            }
            label();
            if (!window.parent._navRowObserver) {
                window.parent._navRowObserver = new MutationObserver(label);
                window.parent._navRowObserver.observe(
                    window.parent.document.body,
                    { childList: true, subtree: true }
                );
            }
        })();
        </script>
    """, height=0)

# ── Step 1 — Setup ───────────────────────────────────────────────────────────
if step == 1:
    def _s1_continue():
        url = st.session_state.get("s1_root_url", "").strip()
        if not url:
            st.error("Please enter a domain URL.")
        else:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            config_mgr.set_value("root_url",     url)
            config_mgr.set_value("source_name",  st.session_state.s1_source_name)
            config_mgr.set_value("purpose_desc", st.session_state.s1_purpose_desc)
            config_mgr.set_value("category_desc",st.session_state.s1_category_desc)
            go(2)

    nav_row(next_label="Continue →", next_key="s1_next", next_fn=_s1_continue)

    with st.container(border=True):
        st.markdown('<div class="step-heading">Project setup</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-desc">Enter the domain you want to index and describe the project.</div>', unsafe_allow_html=True)
        st.text_input("Domain URL", placeholder="https://www.example.com",
                      value=config_mgr.get_value("root_url", ""), key="s1_root_url")
        st.text_input("Website Name", value=config_mgr.get_value("source_name", "My Project"),
                      key="s1_source_name")
        st.text_area("Purpose", value=config_mgr.get_value("purpose_desc",
                     "Provides structured description of the product for AI indexing."),
                     key="s1_purpose_desc", height=80)
        st.text_input("Category", value=config_mgr.get_value("category_desc", "Product documentation"),
                      key="s1_category_desc")

# ── Step 2 — Extract ─────────────────────────────────────────────────────────
elif step == 2:
    root_url = config_mgr.get_value("root_url", "")
    current_state = state_mgr.get_url_state(root_url)
    already_done = current_state.get("status") == "extracted"
    extract_failed = st.session_state.get("s2_extract_failed", False)

    def _s2_back():
        st.session_state.pop("s2_extract_failed", None)
        go(1)

    if already_done:
        nav_row(back_label="← Back", back_key="s2_back", back_fn=_s2_back,
                next_label="Continue →", next_key="s2_next", next_fn=lambda: go(3))
    else:
        nav_row(back_label="← Back", back_key="s2_back", back_fn=_s2_back)

    with st.container(border=True):
        st.markdown('<div class="step-heading">Extract structural links</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="step-desc">Scanning <code>{root_url}</code> — navigations, menus, dropdowns, and footers.</div>', unsafe_allow_html=True)
        if already_done:
            link_tree = current_state["link_tree"]
            total = sum(len(v) for v in link_tree.values())
            st.success(f"Found {total} links across {len(link_tree)} categories.")
            render_link_tree(link_tree)
        elif extract_failed:
            st.error("Could not reach the domain or no links were found.")
            if st.button("Retry", key="s2_retry"):
                st.session_state.pop("s2_extract_failed", None)
                st.rerun()
        else:
            with st.spinner("Rendering page and extracting links…"):
                extracted = asyncio.run(process_single_page(root_url))
                if extracted and extracted.get("link_tree"):
                    state_mgr.update_url_state(root_url, {
                        "status": "extracted",
                        "link_tree": extracted["link_tree"]
                    })
                    st.rerun()
                else:
                    st.session_state.s2_extract_failed = True
                    st.rerun()

# ── Step 3 — Generate ────────────────────────────────────────────────────────
elif step == 3:
    root_url = config_mgr.get_value("root_url", "")
    link_tree = state_mgr.get_url_state(root_url).get("link_tree", {})
    parsed_url = urlparse(root_url)
    combined_prompt = DEFAULT_PROMPT_TEMPLATE.format(
        url=root_url, domain=parsed_url.netloc
    ) + "\n" + json.dumps(link_tree, indent=2)

    def _s3_continue():
        val = st.session_state.get("s3_ai_result", "").strip()
        if not val:
            st.error("Paste the AI-generated Markdown before continuing.")
        else:
            # Persist to a plain key before rerun wipes the widget key
            st.session_state.s3_ai_result_saved = val
            go(4)

    nav_row(back_label="← Back", back_key="s3_back", back_fn=lambda: go(2),
            next_label="Continue →", next_key="s3_next", next_fn=_s3_continue)

    with st.container(border=True):
        st.markdown('<div class="step-heading">Generate with AI</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-desc">Copy the prompt below, paste it into your AI of choice, then paste the result back here.</div>', unsafe_allow_html=True)
        st.code(combined_prompt, language="markdown")
        copy_button(combined_prompt, key="s3_prompt")

    with st.container(border=True):
        st.markdown('<div class="step-heading">Paste AI output</div>', unsafe_allow_html=True)
        st.text_area("AI Output", label_visibility="collapsed", height=260,
                     placeholder="## Documentation\n- [Page](URL): Description…",
                     key="s3_ai_result")

# ── Step 4 — Download ────────────────────────────────────────────────────────
elif step == 4:
    source_name   = config_mgr.get_value("source_name", "My Project")
    purpose_desc  = config_mgr.get_value("purpose_desc", "")
    category_desc = config_mgr.get_value("category_desc", "")
    root_url      = config_mgr.get_value("root_url", "")
    ai_result     = st.session_state.get("s3_ai_result_saved", "")

    header = (
        f"# llms.txt\n"
        f"# Source: {source_name}\n"
        f"# Purpose: {purpose_desc}\n"
        f"# Spec: https://llmstxt.org/\n"
        f"Category: {category_desc}\n"
        f"{'─' * 60}\n\n"
    )
    final_content = header + ai_result.strip() + "\n"

    def _on_download():
        state_mgr.reset_state()
        for k in ["s3_ai_result", "s3_ai_result_saved"]:
            st.session_state.pop(k, None)
        st.session_state.wizard_step = 5

    def _download_widget():
        st.download_button(
            label="Download llms.txt",
            data=final_content,
            file_name="llms.txt",
            mime="text/plain",
            type="primary",
            on_click=_on_download,
        )

    nav_row(back_label="← Back", back_key="s4_back", back_fn=lambda: go(3),
            next_widget=_download_widget)

    with st.container(border=True):
        st.markdown('<div class="step-heading">Your llms.txt is ready</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-desc">Preview and download the generated file.</div>', unsafe_allow_html=True)
        st.code(final_content, language="markdown")
        copy_button(final_content, key="s4_final")

