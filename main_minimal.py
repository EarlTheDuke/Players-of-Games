"""Minimal working version of Players of Games."""
import streamlit as st

def main():
    st.set_page_config(
        page_title="Players of Games - AI vs AI Arena",
        page_icon="🎮",
        layout="wide"
    )
    
    st.title("🎮 Players of Games - AI vs AI Arena")
    st.markdown("**Watch Grok from xAI battle Claude from Anthropic in strategic games!**")
    
    # Test if basic UI works
    st.header("🎯 Chess Game")
    
    # Simple game controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🆕 New Game"):
            st.success("New game button works!")
    
    with col2:
        if st.button("▶️ Next Move"):
            st.info("Next move button works!")
    
    with col3:
        if st.button("⚡ Auto Play"):
            st.info("Auto play button works!")
    
    with col4:
        if st.button("🔄 Reset Game"):
            st.warning("Reset button works!")
    
    # Simple board display
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
    """)
    
    # Sidebar
    st.sidebar.header("Game Configuration")
    game_type = st.sidebar.selectbox("Select Game", ["Chess", "Tic-Tac-Toe"])
    player1 = st.sidebar.selectbox("Player 1", ["Grok", "Claude"])
    player2 = st.sidebar.selectbox("Player 2", ["Claude", "Grok"])
    
    st.sidebar.success("✅ Minimal UI loaded successfully!")

if __name__ == "__main__":
    main()
