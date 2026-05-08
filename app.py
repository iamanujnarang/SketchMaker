import streamlit as st
import pandas as pd
import numpy as np
import graphviz
from fpdf import FPDF
import tempfile
import os
import math

# ---------------- CONFIG & ASSETS ----------------
st.set_page_config(page_title="PSPCL Feeder Sketch Pro", page_icon="⚡", layout="wide")

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
    .main-header {{ text-align: center; padding: 20px; background: white; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
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
st.markdown(f'<div class="main-header"><img src="{PSPCL_LOGO_UI}" height="100"><h1>11kV Feeder Sketch & SLD Master</h1></div>', unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Sketch Identity")
    feeder_name = st.text_input("Feeder Name", "New Garden Enclave")
    substation = st.text_input("Substation Name", "132kV MALL MANDI")
    mdi_a = st.number_input("Max Demand (Amps)", value=170.0)
    mdi_kva = round(np.sqrt(3) * 11 * mdi_a, 2)
    st.success(f"Calculated MDI: {mdi_kva} kVA")

# ---------------- INPUT TABLES ----------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🚠 Backbone (Main Line)")
    n_sec = st.number_input("Number of Sections", min_value=1, value=3, step=1)
    main_sections = [f"{chr(65+i)}-{chr(66+i)}" for i in range(int(n_sec))]
    main_df = pd.DataFrame({
        "SECTION": main_sections,
        "CONDUCTOR": ["ACSR 80 SQMM"] * len(main_sections),
        "LENGTH_MTR": [500.0] * len(main_sections),
        "LOAD_KVA": [100.0] * len(main_sections)
    })
    edited_main_df = st.data_editor(main_df, use_container_width=True, key="main_tbl")

with col_right:
    st.subheader("🌿 T-Offs / Sub-Branches")
    # Node list for connection points (B, C, D...)
    node_options = [s.split('-')[1] for s in main_sections]
    branch_df = pd.DataFrame({
        "CONNECT_AT": [node_options[0]] if node_options else [None],
        "BRANCH_NAME": ["Branch 1"],
        "CONDUCTOR": ["ACSR 50 SQMM"],
        "LENGTH_MTR": [200.0],
        "LOAD_KVA": [50.0]
    })
    edited_branch_df = st.data_editor(branch_df, num_rows="dynamic", use_container_width=True, 
                                     column_config={"CONNECT_AT": st.column_config.SelectboxColumn(options=node_options)},
                                     key="br_tbl")

# ---------------- SKETCH ENGINE ----------------
def create_feeder_graph(m_df, b_df, ss_name):
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR', size='20,12!', ratio='fill', dpi='300', nodesep='0.5', ranksep='1.0')
    
    # Substation Node
    dot.node("SOURCE", str(ss_name), shape="box3d", style="filled", fillcolor="lightgrey", fontname="Arial-Bold")
    
    # Draw Main Line
    prev_node = "SOURCE"
    for _, row in m_df.iterrows():
        # Get target node name (B, C, D...)
        current_node = str(row['SECTION'].split('-')[1])
        
        # Add Node
        dot.node(current_node, f"Node {current_node}\n{row['LOAD_KVA']} kVA", shape="circle", style="filled", fillcolor="white")
        
        # Link styling
        is_cable = "XLPE" in str(row['CONDUCTOR']).upper()
        p_width = "4.5" if is_cable else "2.0"
        p_color = "#00008B" if is_cable else "black" # Dark Blue for Cable
        
        dot.edge(prev_node, current_node, label=f"{row['LENGTH_MTR']}m\n{row['CONDUCTOR']}", 
                 penwidth=p_width, color=p_color)
        prev_node = current_node

    # Draw T-Offs
    for _, row in b_df.iterrows():
        if row['CONNECT_AT'] and str(row['CONNECT_AT']) != "None":
            target = str(row['CONNECT_AT'])
            br_id = f"BRANCH_{row['BRANCH_NAME']}"
            dot.node(br_id, f"{row['BRANCH_NAME']}\n{row['LOAD_KVA']} kVA", shape="plaintext", fontcolor="#8B0000")
            dot.edge(target, br_id, label=f"{row['LENGTH_MTR']}m", style="dashed", color="red", arrowhead="vee")
            
    return dot

# ---------------- GENERATION BLOCK ----------------
if st.button("🎨 Generate Sketch (Landscape PDF)", use_container_width=True):
    try:
        # Create Graph
        sketch = create_feeder_graph(edited_main_df, edited_branch_df, substation)
        
        # Show on UI
        st.graphviz_chart(sketch, use_container_width=True)

        # PDF Generation
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            sketch.render(tmp.name.replace('.png', ''), format='png', cleanup=True)
            img_path = tmp.name

        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # Top Logo & Title
        pdf.image(PSPCL_SKETCH_LOGO, x=10, y=10, w=40)
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(0, 15, f"{feeder_name.upper()} - FEEDER SINGLE LINE DIAGRAM", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, f"Substation: {substation} | Calculated MDI: {mdi_kva} kVA", ln=True, align='C')
        
        # Insert Large Sketch
        pdf.image(img_path, x=10, y=40, w=275)
        
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        st.download_button("📥 Download Official Sketch (Landscape)", pdf_bytes, f"{feeder_name}_Sketch.pdf")
        
        if os.path.exists(img_path): os.remove(img_path)
            
    except Exception as e:
        st.error(f"Generation Error: {e}. Please ensure all table rows are filled correctly.")

# ---------------- PERMANENT FOOTER ----------------
st.markdown(f"""
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
""", unsafe_allow_html=True)
