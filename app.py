import streamlit as st

# Your provided GitHub Logo URL
SKETCH_LOGO_URL = "https://raw.githubusercontent.com/iamanujnarang/SketchMaker/refs/heads/main/PSPCLLogo.png"

def generate_header(feeder_name, subdivision):
    # This logic creates the top section of the sketch
    header_svg = f"""
    <svg width="800" height="100">
        <image href="{SKETCH_LOGO_URL}" x="10" y="10" width="80" />
        
        <text x="100" y="40" font-weight="bold" font-size="20">{feeder_name}</text>
        <text x="100" y="65" font-size="14">Punjab State Power Corporation Limited</text>
        <text x="100" y="85" font-size="12">{subdivision}</text>
        
        <line x1="0" y1="95" x2="800" y2="95" stroke="black" stroke-width="2" />
    </svg>
    """
    return header_svg

# User Inputs
st.sidebar.header("Feeder Identity")
name = st.sidebar.text_input("Feeder Name", "11kV New Garden Enclave")
sd = st.sidebar.text_input("Subdivision", "Mall Mandi")

# Display Header
st.markdown(generate_header(name, sd), unsafe_allow_html=True)
