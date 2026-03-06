import streamlit as st
import asyncio
import os
import aiohttp
from state_manager import StateManager
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

ICONS = {
    "doc": 'https://www.svgrepo.com/show/512226/file-txt-1733.svg',
    "gear": 'https://www.svgrepo.com/show/471873/settings-02.svg',
    "upload": 'https://www.svgrepo.com/show/471878/share-02.svg',
    "extract": 'https://www.svgrepo.com/show/471319/dataflow-04.svg',
    "generate": 'https://www.svgrepo.com/show/470967/annotation-dots.svg',
    "map": 'https://www.svgrepo.com/show/512461/map-161.svg',
}

def get_icon(name, size=20):
    url = ICONS.get(name)
    return f'<img src="{url}" style="width:{size}px; height:{size}px; filter: invert(1); vertical-align: middle; margin-right: 10px; opacity: 0.8;" />'

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Shadcn Dark Theme Overrides */
    :root {
        --background: 0 0% 3.9%;
        --foreground: 0 0% 98%;
        --muted: 0 0% 63.9%;
        --muted-foreground: 0 0% 45.1%;
        --border: 0 0% 14.9%;
        --primary: 0 0% 98%;
    }

    /* Global font set at container level */
    .stApp, .stApp [data-testid="stWidgetLabel"], .stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        font-family: 'Inter', sans-serif !important;
        color: #fafafa !important;
    }
    
    /* PROTECT ICONS: Ensure ligatures work by restoring default font for icon containers */
    [data-testid="stIconMaterial"], 
    .st-emotion-cache-1v0vhou, 
    span[data-testid="stText"] {
        font-family: "Material Symbols Rounded" !important;
    }

    /* Fixed overlap in expanders & Nuclear hide on all default icons/arrows */
    .stExpander summary {
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
        padding: 0.5rem 1rem !important;
        border-bottom: 1px solid #27272a !important;
    }
    
    /* Hide EVERY possible icon element in the summary */
    .stExpander summary svg,
    .stExpander summary [data-testid="stExpanderChevron"],
    .stExpander summary [class*="Icon"],
    .stExpander summary [class*="chevron"],
    .stExpander summary span:empty,
    .stExpander summary div:empty {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        visibility: hidden !important;
    }

    /* Force Inter font precisely without breaking icons */
    .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, 
    .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp summary {
        font-family: 'Inter', sans-serif !important;
    }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    
    .svg-icon {
        width: 1.1rem;
        height: 1.1rem;
        display: inline-block;
        vertical-align: -0.2rem;
        margin-right: 4px;
        fill: none;
        stroke: currentColor;
        color: #71717a;
    }
    
    .custom-header {
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 2px;
        margin: 1.5rem 0 0.5rem 0;
        color: #fafafa;
        line-height: normal;
    }
    
    .sub-text {
        font-size: 0.85rem;
        color: #a1a1aa;
        margin-bottom: 1.25rem;
        line-height: 1.5;
    }

    /* Sidebar tweaks */
    [data-testid="stSidebar"] div.stMarkdown h2, 
    [data-testid="stSidebar"] .custom-header {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    label[data-testid="stWidgetLabel"] p {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: #e4e4e7 !important;
        margin-bottom: 6px !important;
    }
    
    /* Link Grid Layout */
    .link-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 0.8rem 1.2rem;
        font-size: 0.75rem;
        padding: 0.5rem 0 1rem 0;
    }
    
    .link-item {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #a1a1aa;
    }
    
    .link-item a {
        color: #60a5fa !important;
        text-decoration: none;
    }
    
    .link-item a:hover {
        text-decoration: underline;
    }
    
    .category-title {
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 0px;
        margin-bottom: 0.6rem;
        border-bottom: 1px solid #27272a;
        padding-bottom: 4px;
        color: #71717a;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Scrollable Containers */
    .scroll-container {
        max-height: 400px;
        overflow-y: auto;
        padding-right: 10px;
    }
    
    div[data-testid="stCodeBlock"], .stCode {
        max-height: 300px !important;
        overflow-y: auto !important;
        background-color: #09090b !important;
    }

    /* Streamlit Button Tweaks */
    div.stButton > button {
        border-radius: 6px;
        font-size: 0.85rem;
        padding: 0.4rem 1.25rem;
        font-weight: 500;
    }

    /* Expander Styling */
    .stExpander {
        border: 1px solid #27272a !important;
        background: transparent !important;
    }

    .st-emotion-cache-zy6yx3 {
        padding: 20px 60px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize robust state tracking
state_mgr = StateManager()
config_mgr = ConfigManager()

# Persist helpers
def save_config(key, session_key):
    config_mgr.set_value(key, st.session_state[session_key])


st.markdown(f'<div style="font-size: 32px;" class="custom-header">{get_icon("doc", 32)} llms.txt Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Generate a structural map of your domain for AI indexing.</div>', unsafe_allow_html=True)

# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown(f'<div class="custom-header" style="margin-top:0;">{get_icon("gear", 18)} Settings</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    source_name = st.text_input(
        "Website Name", 
        value=config_mgr.get_value("source_name", "My Project"),
        key="ui_source_name",
        on_change=save_config,
        args=("source_name", "ui_source_name")
    )
    purpose_desc = st.text_area(
        "Purpose", 
        value=config_mgr.get_value("purpose_desc", "Provides structured description of the product for AI indexing."),
        key="ui_purpose_desc",
        on_change=save_config,
        args=("purpose_desc", "ui_purpose_desc")
    )
    category_desc = st.text_input(
        "Category", 
        value=config_mgr.get_value("category_desc", "Product documentation"),
        key="ui_category_desc",
        on_change=save_config,
        args=("category_desc", "ui_category_desc")
    )
    
    st.markdown("---")

# --- Main App ---
st.markdown(f'<div class="custom-header">{get_icon("upload", 20)} 1. Enter Root Domain</div>', unsafe_allow_html=True)
root_url = st.text_input(
    "Domain URL", 
    placeholder="https://www.example.com",
    label_visibility="collapsed",
    value=config_mgr.get_value("root_url", "")
)

if root_url:
    # Save URL choice
    if root_url != config_mgr.get_value("root_url", ""):
        config_mgr.set_value("root_url", root_url)

    st.markdown(f'<div class="custom-header">{get_icon("extract", 20)} 2. Extract Structural Links</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-text">Analyze the page navigation and footer structure.</div>', unsafe_allow_html=True)

    if st.button("Start Extraction", type="primary"):
        with st.spinner("Scraping domain structure..."):
            extracted_data = asyncio.run(process_single_page(root_url))
            if extracted_data and extracted_data.get("link_tree"):
                state_mgr.update_url_state(root_url, {
                    "status": "extracted",
                    "link_tree": extracted_data["link_tree"]
                })
                st.toast(f"Found {len(extracted_data['link_tree'])} categories!", icon="✅")
            else:
                st.error("Could not reach the domain or no links were found.")

    # Check if we have extracted data
    current_state = state_mgr.get_url_state(root_url)
    if current_state.get("status") == "extracted":
        link_tree = current_state.get("link_tree", {})
        
        with st.expander("🗺️ Discovered Navigation Map", expanded=True):
            st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
            for category, links in link_tree.items():
                st.markdown(f'<div class="category-title">{category}</div>', unsafe_allow_html=True)
                cols_html = "".join([f'<div class="link-item">• <a href="{l["url"]}" target="_blank">{l["text"]}</a></div>' for l in links])
                st.markdown(f'<div class="link-grid">{cols_html}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="custom-header">{get_icon("generate", 18)} 3. Generate llms.txt</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-text">Copy the prompt below for AI synthesis.</div>', unsafe_allow_html=True)
        
        parsed_url = urlparse(root_url)
        prompt_header = DEFAULT_PROMPT_TEMPLATE.format(
            url=root_url,
            domain=parsed_url.netloc,
        )
        combined_prompt = f"{prompt_header}\n{json.dumps(link_tree, indent=2)}"
        
        # Standard code block for native copy button
        st.code(combined_prompt, language="markdown")
        
        st.markdown(f'<br><div class="custom-header">{get_icon("doc", 18)} AI Result</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-text">Paste the generated Markdown content here.</div>', unsafe_allow_html=True)
        pasted_ai_result = st.text_area("AI Output", label_visibility="collapsed", height=250, placeholder="## Documentation\n- [Page](URL): Description...")
            
        if st.button("Generate Final llms.txt", type="primary") and pasted_ai_result.strip():
            final_content = f"# llms.txt\n"
            final_content += f"# Source: {source_name}\n"
            final_content += f"# Purpose: {purpose_desc}\n"
            final_content += f"# Spec: https://llmstxt.org/\n"
            final_content += f"Category: {category_desc}\n"
            final_content += "-" * 60 + "\n"
            final_content += pasted_ai_result.strip() + "\n"
            
            st.toast("File generated successfully!", icon="📄")
            st.download_button(
                label="Download llms.txt",
                data=final_content,
                file_name="llms.txt",
                mime="text/plain"
            )
        
        st.markdown("---")
        if st.button("Reset State"):
            state_mgr.reset_state()
            st.rerun()
    else:
        st.info("Enter a domain and run extraction to proceed.")
