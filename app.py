import streamlit as st
import pandas as pd
import numpy as np
import graphviz
from fpdf import FPDF
import tempfile
import os

# ---------------- CONFIG & ASSETS ----------------
st.set_page_config(page_title="PSPCL Feeder Sketch Pro", page_icon="⚡", layout="wide")

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
    .footer-container {{ text-align: center; margin-top: 80px; padding: 40px 20px; border-top: 1px solid #ddd; }}
    .social-icon {{ width: 35px; margin: 0 10px; transition: 0.3s; }}
    .social-icon:hover {{ transform: scale(1.2); }}
    .beeclue-img {{ width: 180px; height: auto; }}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown(f'<div class="main-header"><img src="{PSPCL_LOGO_UI}" height="100"><h1>11kV Feeder Sketch & SLD Master</h1></div>', unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Sketch Details")
    feeder_name = st.text_input("Feeder Name", "New Garden Enclave")
    substation = st.text_input("Substation Name", "132kV MALL MANDI")
    mdi_a = st.number_input("Max Demand (Amps)", value=170.0)
    mdi_kva = round(np.sqrt(3) * 11 * mdi_a, 2)
    st.success(f"MDI: {mdi_kva} kVA")

# ---------------- INPUT TABLES ----------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🚠 Backbone (Main Line)")
    n_sec = st.number_input("Main Sections", min_value=1, value=3)
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
    branch_nodes = [s.split('-')[1] for s in main_sections]
    branch_df = pd.DataFrame({
        "CONNECT_AT": [branch_nodes[0]] if branch_nodes else [],
        "BRANCH_NAME": ["Branch 1"],
        "CONDUCTOR": ["ACSR 50 SQMM"],
        "LENGTH_MTR": [200.0],
        "LOAD_KVA": [50.0]
    })
    edited_branch_df = st.data_editor(branch_df, num_rows="dynamic", use_container_width=True, key="br_tbl")

# ---------------- SKETCH LOGIC ----------------
def create_feeder_graph(main_df, branch_df, ss_name, f_name):
    dot = graphviz.Digraph(format='png')
    # Graph size bada karne ke liye aur landscape feel ke liye
    dot.attr(rankdir='LR', size='20,15!', ratio='fill', dpi='300')
    
    # Substation (Dynamic from User Input)
    dot.node("SS", ss_name, shape="box3d", style="filled", fillcolor="lightyellow", fontsize="14", fontname="Arial-Bold")
    
    # Main Backbone
    last_node = "SS"
    for _, row in main_df.iterrows():
        nodes = row['SECTION'].split('-')
        end_node = nodes[1]
        
        # Node Style
        dot.node(end_node, f"Node {end_node}\n({row['LOAD_KVA']} kVA)", shape="circle", style="filled", fillcolor="lightblue")
        
        # Cable Type Logic
        is_cable = "XLPE" in row['CONDUCTOR'].upper()
        p_width = "4" if is_cable else "2"
        p_color = "darkblue" if is_cable else "black"
        
        dot.edge(last_node, end_node, label=f"{row['LENGTH_MTR']}m\n{row['CONDUCTOR']}", 
                 penwidth=p_width, color=p_color, fontname="Arial")
        last_node = end_node

    # T-Offs (Loop Wire Style)
    for _, row in branch_df.iterrows():
        br_id = f"BR_{row['BRANCH_NAME']}"
        dot.node(br_id, f"{row['BRANCH_NAME']}\n{row['LOAD_KVA']} kVA", shape="plaintext", fontcolor="darkred")
        dot.edge(row['CONNECT_AT'], br_id, label=f"{row['LENGTH_MTR']}m", style="dashed", color="red", arrowhead="vee")

    return dot

# ---------------- DISPLAY & EXPORT ----------------
if st.button("🚀 Generate High-Resolution Sketch", use_container_width=True):
    sketch = create_feeder_graph(edited_main_df, edited_branch_df, substation, feeder_name)
    
    # Bada view dikhane ke liye
    st.graphviz_chart(sketch, use_container_width=True)

    # PDF EXPORT (LANDSCAPE)
    try:
        # Temp files to handle graphviz output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            sketch.render(tmp_file.name.replace('.png', ''), format='png', cleanup=True)
            img_path = tmp_file.name
        
        pdf = FPDF(orientation='L', unit='mm', format='A4') # LANDSCAPE
        pdf.add_page()
        
        # Header with Logo
        pdf.image(PSPCL_SKETCH_LOGO, x=10, y=10, w=40)
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(0, 15, f"{feeder_name.upper()} - 11kV FEEDER SKETCH", ln=True, align='C')
        pdf.set_font("Arial", 'I', 12)
        pdf.cell(0, 10, f"Substation: {substation} | MDI: {mdi_kva} kVA", ln=True, align='C')
        pdf.ln(5)

        # INSERT SKETCH IMAGE (Centered and Large)
        pdf.image(img_path, x=10, y=45, w=275) # Full width for landscape

        pdf_output = pdf.output(dest='S').encode('latin1')
        st.download_button("📥 Download Landscape Sketch PDF", pdf_output, f"{feeder_name}_Sketch.pdf")
        
        # Cleanup
        if os.path.exists(img_path): os.remove(img_path)
            
    except Exception as e:
        st.error(f"Sketch export error: {e}. Make sure 'graphviz' is installed on your system.")

# ---------------- FOOTER ----------------
st.markdown(f"""
<div class="footer-container">
    <div>Made with ❤️ by <b>Er. Anuj Narang, JE PSPCL</b></div>
    <div style="margin: 20px 0;">
        <a href="https://instagram.com/iamanujnarang"><img src="{SOCIAL_ICONS['insta']}" class="social-icon"></a>
        <a href="https://facebook.com/iamanujnarang"><img src="{SOCIAL_ICONS['fb']}" class="social-icon"></a>
        <a href="https://x.com/iamanujnarang"><img src="{SOCIAL_ICONS['x']}" class="social-icon"></a>
        <a href="https://linkedin.com/in/iamanujnarang"><img src="{SOCIAL_ICONS['li']}" class="social-icon"></a>
    </div>
    <img src="{BEECLUE_LOGO}" class="beeclue-img">
    <p style="color: #94a3b8; font-size: 0.8rem;">© 2026 | PSPCL DIGITAL TOOLBOX</p>
</div>
""", unsafe_allow_html=True)
