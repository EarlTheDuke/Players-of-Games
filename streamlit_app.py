"""Simple, working Streamlit app for Players of Games."""
import streamlit as st
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import config
    from games.chess_game import ChessGame
    from debug_console import debug_log
    import chess_board_renderer
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Players of Games - AI vs AI Arena",
        page_icon="🎮",
        layout="wide"
    )
    
    st.title("🎮 Players of Games - AI vs AI Arena")
    st.markdown("**Watch Grok from xAI battle Claude from Anthropic in strategic games!**")
    
    # Check API keys
    grok_key_status = "✅ Present" if config.GROK_API_KEY else "❌ Missing"
    claude_key_status = "✅ Present" if config.CLAUDE_API_KEY else "❌ Missing"
    
    # Sidebar
    st.sidebar.header("🔍 Debug Info")
    st.sidebar.text(f"Grok Key: {grok_key_status}")
    st.sidebar.text(f"Claude Key: {claude_key_status}")
    
    if config.GROK_API_KEY:
        st.sidebar.text(f"Grok Preview: {config.GROK_API_KEY[:8]}...")
    if config.CLAUDE_API_KEY:
        st.sidebar.text(f"Claude Preview: {config.CLAUDE_API_KEY[:8]}...")
    
    # Show current models
    st.sidebar.text(f"Grok Model: {config.GROK_MODEL}")
    st.sidebar.text(f"Claude Model: {config.CLAUDE_MODEL}")
    
    # Game configuration
    st.sidebar.header("Game Configuration")
    game_type = st.sidebar.selectbox("Select Game", ["Chess"])
    
    st.sidebar.subheader("Players")
    player1 = st.sidebar.selectbox("Player 1", ["Grok"], index=0)
    player2 = st.sidebar.selectbox("Player 2", ["Claude"], index=0)
    
    # API key warning
    api_keys_ok = bool(config.GROK_API_KEY and config.CLAUDE_API_KEY)
    if not api_keys_ok:
        st.warning("⚠️ API Keys Required: This app requires API keys from xAI (Grok) and Anthropic (Claude) to function.")
    else:
        st.success("✅ API keys configured! Ready to play games.")
    
    # Test API connections
    if st.sidebar.button("🔍 Test API Connections"):
        with st.spinner("Testing APIs..."):
            try:
                from api_utils import call_grok, call_claude
                
                # Test Grok
                grok_result = call_grok("Test", config.GROK_API_KEY, config.GROK_MODEL)
                if grok_result:
                    st.sidebar.success(f"✅ Grok API working ({config.GROK_MODEL}): {grok_result[:20]}...")
                else:
                    st.sidebar.error("❌ Grok API failed - check server logs")
                
                # Test Claude  
                claude_result = call_claude("Test", config.CLAUDE_API_KEY, config.CLAUDE_MODEL)
                if claude_result:
                    st.sidebar.success(f"✅ Claude API working: {claude_result[:20]}...")
                else:
                    st.sidebar.error("❌ Claude API failed - check server logs")
                    
            except Exception as e:
                st.sidebar.error(f"❌ API test failed: {e}")
    
    # Main game area
    st.header("🎯 Chess Game")
    
    # Game controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🆕 New Game"):
            if 'game' in st.session_state:
                del st.session_state.game
            st.session_state.game_started = True
            st.rerun()
    
    with col2:
        if st.button("▶️ Next Move"):
            if 'game' in st.session_state:
                st.session_state.make_move = True
                st.rerun()
    
    with col3:
        if st.button("⏩ Auto Play"):
            st.session_state.auto_play = not st.session_state.get('auto_play', False)
            st.rerun()
    
    with col4:
        if st.button("🔄 Reset Game"):
            if 'game' in st.session_state:
                del st.session_state.game
            st.session_state.clear()
            st.rerun()
    
    # Initialize game if needed
    if st.session_state.get('game_started', False) and 'game' not in st.session_state:
        try:
            players = {'player1': 'grok', 'player2': 'claude'}
            st.session_state.game = ChessGame(players, log_to_file=False)
            st.success("✅ New chess game started!")
        except Exception as e:
            st.error(f"❌ Failed to create game: {e}")
    
    # Display game if it exists
    if 'game' in st.session_state:
        game = st.session_state.game
        
        # Make move if requested
        if st.session_state.get('make_move', False):
            st.session_state.make_move = False
            try:
                with st.spinner("AI is thinking..."):
                    success = game.make_move()
                    if not success:
                        st.error("❌ Move failed")
                    else:
                        st.success("✅ Move completed")
            except Exception as e:
                st.error(f"❌ Move error: {e}")
        
        # Display board
        try:
            # Create proper player mapping for the renderer (it expects 'white' and 'black' keys)
            player_names = {
                'white': 'White (Grok)', 
                'black': 'Black (Claude)'
            }
            board_html = chess_board_renderer.render_chess_board_with_info(
                game.board, 
                player_names
            )
            st.components.v1.html(board_html, height=520, width=660)
        except Exception as e:
            st.error(f"❌ Board display error: {e}")
            # Fallback to simple board renderer
            try:
                simple_board_html = chess_board_renderer.render_chess_board(game.board)
                st.components.v1.html(simple_board_html, height=400, width=400)
            except Exception as e2:
                st.error(f"❌ Simple board error: {e2}")
                # Final fallback to text display
                st.code(str(game.board))
        
        # Game info
        st.subheader("📊 Game Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Player", game.current_player)
            st.metric("Move Count", game.move_count)
        
        with col2:
            st.metric("Turn", "White" if game.board.turn else "Black")
            st.metric("Is Check", "Yes" if game.board.is_check() else "No")
        
        with col3:
            st.metric("Is Checkmate", "Yes" if game.board.is_checkmate() else "No")
            st.metric("Legal Moves", len(list(game.board.legal_moves)))
        
        # Show FEN
        st.text(f"FEN: {game.board.fen()}")
        
        # Game log
        st.subheader("📝 Game Log")
        try:
            # Access the game history directly from the logger
            if hasattr(game.logger, 'game_history'):
                log_entries = game.logger.game_history
                if log_entries:
                    for entry in log_entries[-5:]:  # Show last 5 moves
                        if isinstance(entry, dict) and 'move' in entry:
                            status = "✅" if entry.get('is_valid', True) else "❌"
                            move = entry.get('move', 'Unknown')
                            reasoning = entry.get('reasoning', 'No reasoning')[:100]
                            player = entry.get('player', 'Unknown')
                            move_num = entry.get('move_number', '?')
                            st.text(f"{status} Move {move_num} - {player.upper()}: {move}")
                            st.text(f"   Reasoning: {reasoning}...")
                            st.text("")  # Empty line for spacing
                else:
                    st.text("No moves yet - click 'Next Move' to start!")
            else:
                st.text("Game log not available - moves will appear here")
        except Exception as e:
            st.text(f"Game log error: {e}")
            st.text("Moves will appear here when the game starts")
    
    # Debug console
    st.sidebar.subheader("🖥️ Debug Console")
    try:
        from debug_console import debug_console
        messages = list(debug_console.messages)
        if messages:
            for msg in messages[-5:]:  # Show last 5 debug messages
                st.sidebar.text(f"[{msg['timestamp']}] {msg['message'][:50]}...")
        else:
            st.sidebar.text("No debug messages")
    except Exception as e:
        st.sidebar.error(f"Debug error: {e}")

if __name__ == "__main__":
    main()
