"""Streamlit Cloud entry point for Players of Games - Emergency Minimal Version."""
import streamlit as st

# Configure the page
st.set_page_config(
    page_title="Players of Games - AI vs AI Arena",
    page_icon="🎮",
    layout="wide"
)

# Title and description
st.title("🎮 Players of Games - AI vs AI Arena")
st.markdown("**Watch Grok from xAI battle Claude from Anthropic in strategic games!**")

# Test message
st.success("✅ Emergency minimal version loaded successfully!")

# Main content
st.header("🎯 Chess Game")

# Game controls in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🆕 New Game"):
        st.success("✅ New Game button clicked!")

with col2:
    if st.button("▶️ Next Move"):
        st.info("ℹ️ Next Move button clicked!")

with col3:
    if st.button("⚡ Auto Play"):
        st.info("ℹ️ Auto Play button clicked!")

with col4:
    if st.button("🔄 Reset Game"):
        st.warning("⚠️ Reset button clicked!")

# Game board display
st.subheader("🎯 Current Position")
st.code("""
r n b q k b n r
p p p p p p p p
. . . . . . . .
. . . . . . . .
. . . . P . . .
. . . . . . . .
P P P P . P P P
R N B Q K B N R
""", language="text")

# Sidebar configuration
st.sidebar.header("🎮 Game Configuration")
st.sidebar.success("✅ Sidebar loaded!")

game_type = st.sidebar.selectbox(
    "Select Game",
    ["Chess", "Tic-Tac-Toe"],
    index=0
)

player1 = st.sidebar.selectbox(
    "Player 1",
    ["Grok", "Claude"],
    index=0
)

player2 = st.sidebar.selectbox(
    "Player 2",
    ["Claude", "Grok"],
    index=0
)

# Show configuration
st.sidebar.write(f"**Game:** {game_type}")
st.sidebar.write(f"**Player 1:** {player1}")
st.sidebar.write(f"**Player 2:** {player2}")

# Debug info
st.subheader("🔧 Debug Info")
st.write("If you can see this message, Streamlit is working correctly!")
st.json({
    "game_type": game_type,
    "player1": player1,
    "player2": player2,
    "status": "Minimal version running"
})

# Footer
st.markdown("---")
st.markdown("**🚨 This is an emergency minimal version to test basic functionality.**")