import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF
from datetime import datetime

# ---------------- CONFIG & ASSETS ----------------
st.set_page_config(page_title="PSPCL Feeder Sketch Maker", page_icon="🔌", layout="wide")

# Assets
PSPCL_LOGO_UI = "https://pspcl.in/assets/images/logo.png"
PSPCL_SKETCH_LOGO = "https://raw.githubusercontent.com/iamanujnarang/SketchMaker/refs/heads/main/PSPCLLogo.png"
BEECLUE_LOGO = "https://raw.githubusercontent.com/iamanujnarang/LDHF/e5748e037b76a52a47d610a88c3a3c70f72f1c9a/BEECLUE.png"
SOCIAL_ICONS = {
    "insta": "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png",
    "fb": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg",
    "x": "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg",
    "li": "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
}

VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415, "ACSR 80 SQMM": 0.0512, "ACSR 50 SQMM": 0.0910,
    "XLPE 300 SQMM": 0.0146, "XLPE 150 SQMM": 0.0285, "XLPE 35 SQMM": 0.1150
}

# ---------------- CSS ----------------
st.markdown(f"""
<style>
    .main-header {{ text-align: center; padding: 20px; background: white; border-radius: 15px; }}
    .footer {{ text-align: center; margin-top: 50px; padding: 30px; border-top: 1px solid #ddd; }}
    .social-logo {{ width: 35px; margin: 0 10px; }}
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
st.subheader("🚠 Main Feeder Backbone (Section A-B-C...)")
n_sec = st.number_input("Number of Main Sections", min_value=1, value=3, step=1)

main_sections = []
for i in range(int(n_sec)):
    main_sections.append(f"{chr(65+i)}-{chr(66+i)}")

main_df = pd.DataFrame({
    "SECTION": main_sections,
    "CONDUCTOR": [list(VD_FACTORS.keys())[0]] * len(main_sections),
    "LENGTH (Mtr)": [500.0] * len(main_sections),
    "CONNECTED LOAD (kVA)": [1000.0] * len(main_sections)
})

edited_main_df = st.data_editor(main_df, column_config={
    "CONDUCTOR": st.column_config.SelectboxColumn(options=list(VD_FACTORS.keys()))
}, use_container_width=True, key="main_table")

st.divider()

st.subheader("🌿 Sub-Branches / T-Offs (Connects at Nodes)")
# Mapping Sub-Branches to nodes (B, C, D...)
branch_nodes = [s.split('-')[1] for s in main_sections]
branch_df = pd.DataFrame({
    "CONNECT AT NODE": [branch_nodes[0]] if branch_nodes else [],
    "BRANCH NAME": ["T-Off 1"],
    "CONDUCTOR": ["ACSR 50 SQMM"],
    "LENGTH (Mtr)": [200.0],
    "LOAD (kVA)": [200.0]
})

edited_branch_df = st.data_editor(branch_df, num_rows="dynamic", column_config={
    "CONNECT AT NODE": st.column_config.SelectboxColumn(options=branch_nodes),
    "CONDUCTOR": st.column_config.SelectboxColumn(options=list(VD_FACTORS.keys()))
}, use_container_width=True, key="branch_table")

# ---------------- SKETCH GENERATION (GRAPHVIZ) ----------------
if st.button("🎨 Generate Sketch & Network Diagram", use_container_width=True):
    dot = graphviz.Digraph(comment=feeder_name)
    dot.attr(rankdir='LR', size='12,8')
    
    # Source
    dot.node("SS", f"132kV\n{subdivision}\nSubstation", shape="box", style="filled", fillcolor="lightgrey")
    
    # Draw Main Backbone
    last_node = "SS"
    for i, row in edited_main_df.iterrows():
        nodes = row['SECTION'].split('-')
        start_node, end_node = nodes[0], nodes[1]
        
        # Draw the node
        dot.node(end_node, f"Node {end_node}\n{row['CONNECTED_LOAD_kVA']} kVA", shape="circle")
        
        # Link main section
        color = "blue" if "XLPE" in row['CONDUCTOR'] else "black"
        dot.edge(last_node, end_node, label=f"{row['LENGTH_Mtr']}m\n{row['CONDUCTOR']}", color=color, penwidth="2")
        last_node = end_node

    # Draw Sub-Branches
    for i, row in edited_branch_df.iterrows():
        b_node = f"BR_{i}"
        dot.node(b_node, f"{row['BRANCH_NAME']}\n{row['LOAD_kVA']} kVA", shape="plaintext")
        dot.edge(row['CONNECT_AT_NODE'], b_node, label=f"{row['LENGTH_Mtr']}m", style="dashed")

    st.graphviz_chart(dot)

    # ---------------- PDF EXPORT ----------------
    # Logic for PDF with specific sketch logo top
    pdf = FPDF()
    pdf.add_page()
    
    # NEW SKETCH LOGO AT TOP
    pdf.image(PSPCL_SKETCH_LOGO, x=10, y=8, w=30)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"     {feeder_name.upper()} FEEDER SKETCH", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"     Sub-Division: {subdivision} | MDI: {mdi_kva} kVA", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Technical Parameters & Load Summary", ln=True)
    pdf.set_font("Arial", size=10)
    
    # Table data in PDF
    for i, row in edited_main_df.iterrows():
        pdf.cell(0, 8, f"Section {row['SECTION']}: {row['LENGTH_Mtr']}m | {row['CONDUCTOR']} | Load: {row['CONNECTED_LOAD_kVA']}kVA", ln=True)
    
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    st.download_button("📥 Download Official Sketch PDF", pdf_bytes, f"{feeder_name}_Sketch.pdf")

# ---------------- FOOTER ----------------
st.markdown(f"""
<div class="footer">
    <p><b>Er. Anuj Narang (JE PSPCL)</b></p>
    <a href="https://instagram.com/iamanujnarang"><img src="{SOCIAL_ICONS['insta']}" class="social-logo"></a>
    <a href="https://facebook.com/iamanujnarang"><img src="{SOCIAL_ICONS['fb']}" class="social-logo"></a>
    <a href="https://x.com/iamanujnarang"><img src="{SOCIAL_ICONS['x']}" class="social-logo"></a>
    <a href="https://linkedin.com/in/iamanujnarang"><img src="{SOCIAL_ICONS['li']}" class="social-logo"></a>
    <br><br>
    <img src="{BEECLUE_LOGO}" width="140">
    <p style="font-size:12px; color: grey;">© 2026 PSPCL | Digital Toolbox | Feeder Sketch Maker v2.0</p>
</div>
""", unsafe_allow_html=True)
