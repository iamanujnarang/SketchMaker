import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF
import math

# ---------------- CONFIG & ASSETS ----------------
st.set_page_config(page_title="PSPCL Feeder Sketch Maker", page_icon="🔌", layout="wide")

# Assets
PSPCL_LOGO_UI = "https://pspcl.in/assets/images/logo.png"
PSPCL_SKETCH_LOGO = "https://raw.githubusercontent.com/iamanujnarang/SketchMaker/refs/heads/main/PSPCLLogo.png"
BEECLUE_LOGO = "https://raw.githubusercontent.com/iamanujnarang/LDHF/e5748e037b76a52a47d610a88c3a3c70f72f1c9a/BEECLUE.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKEDIN_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"

VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415, "ACSR 80 SQMM": 0.0512, "ACSR 50 SQMM": 0.0910,
    "XLPE 300 SQMM": 0.0146, "XLPE 150 SQMM": 0.0285, "XLPE 35 SQMM": 0.1150
}

# ---------------- CSS ----------------
st.markdown(f"""
<style>
    .main-header {{ text-align: center; padding: 20px; background: white; border-radius: 15px; }}
    .footer-container {{ text-align: center; margin-top: 80px; padding: 40px 20px; border-top: 1px solid #ddd; }}
    .made-with-love {{ font-size: 1.2rem; color: #334155; margin-bottom: 20px; }}
    .heart-symbol {{ color: #e63946; }}
    .social-icon {{ width: 35px; margin: 0 10px; transition: 0.3s; }}
    .social-icon:hover {{ transform: scale(1.2); }}
    .powered-text {{ color: #94a3b8; font-size: 0.7rem; letter-spacing: 2px; margin-bottom: 10px; text-transform: uppercase; }}
    .beeclue-img {{ width: 180px; height: auto; }}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown(f'<div class="main-header"><img src="{PSPCL_LOGO_UI}" height="100"><h1>11kV Feeder Sketch & VD Master</h1></div>', unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Feeder Identity")
    feeder_name = st.text_input("Feeder Name", "New Garden Enclave")
    subdivision = st.text_input("Sub-Division", "MALL MANDI")
    mdi_a = st.number_input("Max Demand (Amps)", value=170.0)
    mdi_kva = round(np.sqrt(3) * 11 * mdi_a, 2)
    st.success(f"Calculated MDI: {mdi_kva} kVA")

# ---------------- MAIN INPUT TABLES ----------------
st.subheader("🚠 Main Feeder Backbone (Section A-B, B-C...)")
n_sec = st.number_input("Number of Main Sections", min_value=1, value=3, step=1)

main_sections = [f"{chr(65+i)}-{chr(66+i)}" for i in range(int(n_sec))]

# FIXED: Standardized column names to avoid KeyError
main_df = pd.DataFrame({
    "SECTION": main_sections,
    "CONDUCTOR": ["ACSR 80 SQMM"] * len(main_sections),
    "LENGTH_MTR": [500.0] * len(main_sections),
    "LOAD_KVA": [100.0] * len(main_sections)
})

edited_main_df = st.data_editor(main_df, column_config={
    "CONDUCTOR": st.column_config.SelectboxColumn(options=list(VD_FACTORS.keys()))
}, use_container_width=True, key="main_table")

st.divider()

st.subheader("🌿 Sub-Branches / T-Offs (Connects at Nodes)")
branch_nodes = [s.split('-')[1] for s in main_sections]
branch_df = pd.DataFrame({
    "CONNECT_AT_NODE": [branch_nodes[0]] if branch_nodes else [],
    "BRANCH_NAME": ["T-Off 1"],
    "CONDUCTOR": ["ACSR 50 SQMM"],
    "LENGTH_MTR": [200.0],
    "LOAD_KVA": [50.0]
})

edited_branch_df = st.data_editor(branch_df, num_rows="dynamic", column_config={
    "CONNECT_AT_NODE": st.column_config.SelectboxColumn(options=branch_nodes),
    "CONDUCTOR": st.column_config.SelectboxColumn(options=list(VD_FACTORS.keys()))
}, use_container_width=True, key="branch_table")

# ---------------- SKETCH GENERATION ----------------
if st.button("🎨 Generate Sketch & Network Diagram", use_container_width=True):
    dot = graphviz.Digraph(comment=feeder_name)
    dot.attr(rankdir='LR', size='12,8')
    
    # Source Substation
    dot.node("SS", f"132kV\n{subdivision}\nSubstation", shape="box", style="filled", fillcolor="lightgrey")
    
    # Draw Main Backbone
    last_node = "SS"
    for i, row in edited_main_df.iterrows():
        start_node, end_node = row['SECTION'].split('-')
        
        # Node with Load
        dot.node(end_node, f"Node {end_node}\n{row['LOAD_KVA']} kVA", shape="circle")
        
        # Main line
        color = "blue" if "XLPE" in row['CONDUCTOR'] else "black"
        dot.edge(last_node, end_node, label=f"{row['LENGTH_MTR']}m\n{row['CONDUCTOR']}", color=color, penwidth="2")
        last_node = end_node

    # Draw Sub-Branches
    for i, row in edited_branch_df.iterrows():
        branch_id = f"BR_{i}"
        dot.node(branch_id, f"{row['BRANCH_NAME']}\n{row['LOAD_KVA']} kVA", shape="plaintext")
        dot.edge(row['CONNECT_AT_NODE'], branch_id, label=f"{row['LENGTH_MTR']}m", style="dashed")

    st.graphviz_chart(dot)

    # ---------------- PDF EXPORT ----------------
    pdf = FPDF()
    pdf.add_page()
    
    # PSPCL Sketch Logo at Top
    pdf.image(PSPCL_SKETCH_LOGO, x=10, y=8, w=35)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, f"{feeder_name.upper()} FEEDER SKETCH", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, f"Sub-Division: {subdivision} | Calculated MDI: {mdi_kva} kVA", ln=True, align='C')
    pdf.ln(15)
    
    # Data Table in PDF
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(30, 10, "Section", 1); pdf.cell(60, 10, "Conductor", 1); pdf.cell(40, 10, "Length (m)", 1); pdf.cell(40, 10, "Load (kVA)", 1, ln=True)
    pdf.set_font("Arial", size=10)
    for i, row in edited_main_df.iterrows():
        pdf.cell(30, 8, row['SECTION'], 1)
        pdf.cell(60, 8, row['CONDUCTOR'], 1)
        pdf.cell(40, 8, str(row['LENGTH_MTR']), 1)
        pdf.cell(40, 8, str(row['LOAD_KVA']), 1, ln=True)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    st.download_button("📥 Download Official Sketch PDF", pdf_bytes, f"{feeder_name}_Sketch.pdf")

# ---------------- FOOTER ----------------
footer_html = f"""
<div class="footer-container">
<div class="made-with-love">Made with <span class="heart-symbol">❤️</span> by <b>Er. Anuj Narang, JE PSPCL</b></div>
<div style="margin-bottom: 25px;">
<a href="https://instagram.com/iamanujnarang" target="_blank"><img src="{INSTA_ICON}" class="social-icon"></a>
<a href="https://facebook.com/iamanujnarang" target="_blank"><img src="{FB_ICON}" class="social-icon"></a>
<a href="https://x.com/iamanujnarang" target="_blank"><img src="{X_ICON}" class="social-icon"></a>
<a href="https://linkedin.com/in/iamanujnarang" target="_blank"><img src="{LINKEDIN_ICON}" class="social-icon"></a>
</div>

<div style="margin-top: 25px;">
    <div class="powered-text">In Strategic Collaboration with</div>
    <a href="https://beeclue.com" target="_blank">
        <img src="{BEECLUE_LOGO}" class="beeclue-img">
    </a>
</div>

<div style="color: #94a3b8; font-size: 0.85rem; margin-top: 25px;">© 2026 | PSPCL Guidelines | CC 45/2024</div>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
