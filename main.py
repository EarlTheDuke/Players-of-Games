"""Main entry point for Players of Games."""
import argparse
import sys
import os
from typing import Dict, Any, Optional
import streamlit as st
from games.chess_game import ChessGame
from games.tictactoe_game import TicTacToeGame
import config


def validate_api_keys() -> bool:
    """Validate that required API keys are available."""
    missing_keys = []
    
    if not config.GROK_API_KEY:
        missing_keys.append("GROK_API_KEY")
    if not config.CLAUDE_API_KEY:
        missing_keys.append("CLAUDE_API_KEY")
    
    if missing_keys:
        print("❌ Missing required API keys:")
        for key in missing_keys:
            print(f"   - {key}")
        print("\nPlease set these environment variables or add them to your .env file.")
        print("See .env.example for the required format.")
        return False
    
    return True


def create_game(game_type: str, player1: str, player2: str, log_to_file: bool = True):
    """
    Create a game instance.
    
    Args:
        game_type: Type of game ('chess' or 'tictactoe')
        player1: Model type for player 1 ('grok' or 'claude')
        player2: Model type for player 2 ('grok' or 'claude')
        log_to_file: Whether to log to file
    
    Returns:
        Game instance
    """
    players = {
        'player1': player1.lower(),
        'player2': player2.lower()
    }
    
    if game_type.lower() == 'chess':
        return ChessGame(players, log_to_file)
    elif game_type.lower() == 'tictactoe':
        return TicTacToeGame(players, log_to_file)
    else:
        raise ValueError(f"Unknown game type: {game_type}")


def run_console_game(game_type: str, player1: str, player2: str, 
                    num_games: int = 1, log_to_file: bool = True) -> Dict[str, Any]:
    """
    Run games in console mode.
    
    Args:
        game_type: Type of game to play
        player1: Model type for player 1
        player2: Model type for player 2
        num_games: Number of games to play
        log_to_file: Whether to log to file
    
    Returns:
        Dictionary with game statistics
    """
    results = {
        'games_played': 0,
        'wins': {'player1': 0, 'player2': 0},
        'draws': 0,
        'errors': 0,
        'total_moves': 0,
        'game_results': []
    }
    
    print(f"\n🎮 Starting {num_games} game(s) of {game_type.upper()}")
    print(f"Player 1 ({player1.upper()}) vs Player 2 ({player2.upper()})")
    print("=" * 60)
    
    for game_num in range(num_games):
        print(f"\n🎯 Game {game_num + 1}/{num_games}")
        
        try:
            game = create_game(game_type, player1, player2, log_to_file)
            result = game.play()
            
            results['games_played'] += 1
            results['total_moves'] += result['total_moves']
            results['game_results'].append(result)
            
            if result['result'] == 'win':
                results['wins'][result['winner']] += 1
            elif result['result'] == 'draw':
                results['draws'] += 1
            else:
                results['errors'] += 1
            
            # Export PGN for chess games
            if game_type.lower() == 'chess' and hasattr(game, 'export_pgn'):
                pgn_filename = f"game_{game_num + 1}_{game_type}.pgn"
                game.export_pgn(pgn_filename)
        
        except Exception as e:
            print(f"❌ Error in game {game_num + 1}: {e}")
            results['errors'] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 GAME SUMMARY")
    print("=" * 60)
    print(f"Games played: {results['games_played']}")
    print(f"Player 1 ({player1.upper()}) wins: {results['wins']['player1']}")
    print(f"Player 2 ({player2.upper()}) wins: {results['wins']['player2']}")
    print(f"Draws: {results['draws']}")
    print(f"Errors: {results['errors']}")
    if results['games_played'] > 0:
        avg_moves = results['total_moves'] / results['games_played']
        print(f"Average moves per game: {avg_moves:.1f}")
    
    return results


def run_streamlit_app():
    """Run the Streamlit web interface."""
    st.set_page_config(
        page_title="Players of Games - AI vs AI Arena",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Header with styling
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1>🎮 Players of Games</h1>
        <h3>AI vs AI Game Arena</h3>
        <p>Watch Grok from xAI battle Claude from Anthropic in strategic games!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add usage instructions
    with st.expander("ℹ️ How to Use This App", expanded=False):
        st.markdown("""
        **Welcome to Players of Games!** This app lets you watch AI models compete in real-time:
        
        1. **Select a Game**: Choose Chess or Tic-Tac-Toe from the sidebar
        2. **Choose Players**: Pick which AI models will compete (Grok vs Claude)
        3. **Start Playing**: Click "New Game" to begin, then watch the AIs battle!
        4. **View Analysis**: See move reasoning, game statistics, and position analysis
        
        **Note**: This is a demonstration of AI capabilities. Games may take a few moments as the AIs "think" about their moves.
        """)
    
    # Debug: Show API key status
    st.sidebar.subheader("🔍 Debug Info")
    
    grok_key_status = "✅ Present" if config.GROK_API_KEY else "❌ Missing"
    claude_key_status = "✅ Present" if config.CLAUDE_API_KEY else "❌ Missing"
    
    st.sidebar.text(f"Grok Key: {grok_key_status}")
    st.sidebar.text(f"Claude Key: {claude_key_status}")
    
    if config.GROK_API_KEY:
        st.sidebar.text(f"Grok Key Preview: {config.GROK_API_KEY[:8]}...")
    if config.CLAUDE_API_KEY:
        st.sidebar.text(f"Claude Key Preview: {config.CLAUDE_API_KEY[:8]}...")
    
    # Check for API key configuration
    api_keys_configured = bool(config.GROK_API_KEY and config.CLAUDE_API_KEY and 
                              config.GROK_API_KEY != "test_grok_key_for_local_testing" and
                              config.CLAUDE_API_KEY != "test_claude_key_for_local_testing")
    
    if not api_keys_configured:
        st.warning("""
        ⚠️ **API Keys Required**: This app requires API keys from xAI (Grok) and Anthropic (Claude) to function.
        
        For demo purposes, you can still explore the interface, but games won't work without valid API keys.
        """)
        
        with st.expander("🔑 How to Get API Keys"):
            st.markdown("""
            **To run games with real AI models:**
            
            1. **Grok API Key**: Visit [x.ai](https://x.ai) to sign up and get your API key
            2. **Claude API Key**: Visit [console.anthropic.com](https://console.anthropic.com) to get your API key
            3. **For Streamlit Cloud**: Add keys in the app settings under "Secrets"
            4. **For Local Use**: Add keys to your .env file
            """)
    else:
        st.success("✅ API keys configured! Ready to play games.")
    
    # Sidebar for game configuration
    st.sidebar.header("Game Configuration")
    
    # Game selection
    game_type = st.sidebar.selectbox(
        "Select Game",
        ["Chess", "Tic-Tac-Toe"],
        index=0
    )
    
    # Player selection
    st.sidebar.subheader("Players")
    player1 = st.sidebar.selectbox(
        "Player 1",
        ["Grok", "Claude"],
        index=0
    )
    
    player2 = st.sidebar.selectbox(
        "Player 2", 
        ["Grok", "Claude"],
        index=1
    )
    
    # Game options
    st.sidebar.subheader("Options")
    auto_play = st.sidebar.checkbox("Auto-play moves", value=False)
    show_analysis = st.sidebar.checkbox("Show position analysis", value=True)
    
    # Demo mode when API keys aren't configured
    if not api_keys_configured:
        st.info("🎮 **Demo Mode**: Exploring the interface without API keys")
        
        # Show demo game state
        st.subheader("🎯 Demo Game State")
        
        demo_game_type = st.sidebar.selectbox("Demo Game", ["Chess", "Tic-Tac-Toe"])
        
        if demo_game_type == "Chess":
            st.markdown("**Sample Chess Position:**")
            st.code("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
            st.text("""
    r n b q k b n r
    p p p p p p p p
    . . . . . . . .
    . . . . . . . .
    . . . . P . . .
    . . . . . . . .
    P P P P . P P P
    R N B Q K B N R
            """)
            st.markdown("**Example AI Reasoning:**")
            st.info("🤖 **Grok**: I'll play e2e4 to control the center and open lines for piece development.")
            st.info("🤖 **Claude**: I'll respond with e7e5 to maintain central equality and challenge White's space advantage.")
        
        else:  # Tic-Tac-Toe
            st.markdown("**Sample Tic-Tac-Toe Position:**")
            st.text("""
      0   1   2
    0 X |   | O
      ---------
    1   | X |  
      ---------
    2 O |   |  
            """)
            st.markdown("**Example AI Reasoning:**")
            st.info("🤖 **Grok**: I'll take position 1,2 to block Claude's potential winning line.")
            st.info("🤖 **Claude**: I need to play 2,1 to create a fork and threaten multiple wins.")
        
        st.markdown("---")
        st.markdown("**🔑 Get API keys to play real games with AI models!**")
        return
    
    # Initialize session state
    if 'game' not in st.session_state:
        st.session_state.game = None
    if 'game_history' not in st.session_state:
        st.session_state.game_history = []
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(f"🎯 {game_type} Game")
        
        # Game controls
        col1a, col1b, col1c, col1d = st.columns(4)
        
        with col1a:
            if st.button("🆕 New Game"):
                st.session_state.game = create_game(
                    game_type.lower(), 
                    player1.lower(), 
                    player2.lower(), 
                    log_to_file=False
                )
                st.session_state.game_history = []
                st.success("New game started!")
                st.rerun()
        
        with col1b:
            if st.button("▶️ Next Move") and st.session_state.game:
                if not st.session_state.game.is_game_over():
                    success = st.session_state.game.make_move()
                    if success:
                        st.rerun()
                    else:
                        st.error("Move failed - try resetting the game")
        
        with col1c:
            if st.button("⚡ Auto Play") and st.session_state.game:
                with st.spinner("Playing game..."):
                    result = st.session_state.game.play()
                    st.session_state.game_history.append(result)
                    st.rerun()
        
        with col1d:
            if st.button("🔄 Reset Game") and st.session_state.game:
                # Reset to a fresh game of the same type
                st.session_state.game = create_game(
                    game_type.lower(), 
                    player1.lower(), 
                    player2.lower(), 
                    log_to_file=False
                )
                st.warning("Game reset to starting position")
                st.rerun()
        
        # Display game state
        if st.session_state.game:
            game = st.session_state.game
            
            # Game board
            st.subheader("🎯 Current Position")
            if game_type.lower() == 'chess':
                # Beautiful chess board visualization
                try:
                    from chess_board_renderer import render_chess_board_with_moves
                    
                    # Get last move for highlighting
                    last_move = None
                    if game.board.move_stack:
                        last_move = game.board.peek()
                    
                    # Render beautiful chess board
                    board_html = render_chess_board_with_moves(
                        game.board, 
                        last_move=last_move,
                        board_size=480
                    )
                    st.components.v1.html(board_html, height=520)
                    
                    # Position details in expandable section
                    with st.expander("📋 Position Details (FEN & Text)", expanded=False):
                        st.text("FEN Position:")
                        st.code(game.get_state_text(), language="text")
                        st.text("Text Board:")
                        st.code(game.get_state_display(), language="text")
                    
                except Exception as e:
                    st.error(f"Error rendering chess board: {e}")
                    # Fallback to text board
                    st.code(game.get_state_text(), language="text")
                    st.text(game.get_state_display())
            else:
                # For other games, show board display
                st.text(game.get_state_display())
            
            # Game status
            if game.is_game_over():
                result_type, winner = game.get_game_result()
                if result_type == 'win':
                    st.success(f"🏆 Game Over! Winner: {winner.upper()}")
                elif result_type == 'draw':
                    st.info("🤝 Game ended in a draw!")
                else:
                    st.error("❌ Game ended with an error")
            else:
                current_player = game.current_player
                model = game.players[current_player]
                st.info(f"🎯 Current turn: {current_player.upper()} ({model.upper()})")
            
            # Game info
            if hasattr(game, 'get_game_info'):
                with st.expander("📊 Game Information"):
                    game_info = game.get_game_info()
                    for key, value in game_info.items():
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            
            # Position analysis
            if show_analysis and hasattr(game, 'get_position_analysis'):
                with st.expander("🔍 Position Analysis"):
                    analysis = game.get_position_analysis()
                    for category, data in analysis.items():
                        st.write(f"**{category.replace('_', ' ').title()}:**")
                        if isinstance(data, dict):
                            for key, value in data.items():
                                st.write(f"  - {key.replace('_', ' ').title()}: {value}")
                        else:
                            st.write(f"  {data}")
        
        else:
            st.info("👆 Click 'New Game' to start playing!")
    
    with col2:
        st.header("📝 Game Log")
        
        # Add API Debug Section
        st.subheader("🔧 API Debug Info")
        if st.button("Test API Connections"):
            with st.spinner("Testing API connections..."):
                # Test Grok API
                st.write("**Testing Grok API...**")
                try:
                    from api_utils import call_grok
                    
                    if config.GROK_API_KEY:
                        result = call_grok("Say 'test' in one word.", config.GROK_API_KEY, config.GROK_MODEL)
                        if result:
                            st.success(f"✅ Grok API working: {result}")
                        else:
                            st.error("❌ Grok API failed - check server logs")
                    else:
                        st.error("❌ Grok API key missing")
                except Exception as e:
                    st.error(f"❌ Grok API error: {str(e)}")
                
                # Test Claude API  
                st.write("**Testing Claude API...**")
                try:
                    from api_utils import call_claude
                    
                    if config.CLAUDE_API_KEY:
                        result = call_claude("Say 'test' in one word.", config.CLAUDE_API_KEY, config.CLAUDE_MODEL)
                        if result:
                            st.success(f"✅ Claude API working: {result}")
                        else:
                            st.error("❌ Claude API failed - check server logs")
                    else:
                        st.error("❌ Claude API key missing")
                except Exception as e:
                    st.error(f"❌ Claude API error: {str(e)}")
        
        # Add Game Debug Section
        if st.session_state.game:
            st.subheader("🎯 Game Debug Info")
            
            # Show current game state details
            with st.expander("Current Game State Details"):
                if hasattr(st.session_state.game, 'board'):  # Chess game
                    st.write(f"**FEN**: {st.session_state.game.get_state_text()}")
                    st.write(f"**Turn**: {'White' if st.session_state.game.board.turn else 'Black'}")
                    st.write(f"**Move Count**: {st.session_state.game.board.fullmove_number}")
                    st.write(f"**Current Player**: {st.session_state.game.current_player}")
                    
                    # Show player color mapping
                    if hasattr(st.session_state.game, 'player_colors'):
                        st.write("**Player Colors**:")
                        for player, color in st.session_state.game.player_colors.items():
                            color_name = "White" if color else "Black"
                            st.write(f"  - {player}: {color_name}")
                    
                    # Show legal moves
                    legal_moves = st.session_state.game.get_legal_actions()
                    st.write(f"**Legal Moves ({len(legal_moves)})**: {', '.join(legal_moves[:10])}{'...' if len(legal_moves) > 10 else ''}")
                
                else:  # Other games
                    st.write(f"**Game State**: {st.session_state.game.get_state_text()}")
                    st.write(f"**Current Player**: {st.session_state.game.current_player}")
                    legal_moves = st.session_state.game.get_legal_actions()
                    st.write(f"**Legal Moves**: {', '.join(legal_moves)}")
        
        # Add Live Debug Console
        st.subheader("🖥️ Live Debug Console")
        
        col_debug1, col_debug2 = st.columns([3, 1])
        
        with col_debug1:
            if st.button("🔄 Refresh Debug Log"):
                st.rerun()
        
        with col_debug2:
            if st.button("🗑️ Clear Debug Log"):
                try:
                    from debug_console import debug_console
                    debug_console.clear()
                    st.success("Debug log cleared")
                except:
                    pass
        
        # Show debug messages
        try:
            from debug_console import debug_console
            messages = debug_console.get_messages(15)
            
            if messages:
                st.text("Recent Debug Messages:")
                debug_text = ""
                for msg in messages:
                    debug_text += f"[{msg['timestamp']}] {msg['level']}: {msg['message']}\n"
                st.code(debug_text, language="text")
            else:
                st.info("No debug messages yet. Make a move to see debug output.")
        except Exception as e:
            st.warning(f"Debug console not available: {e}")
        
        if st.session_state.game and hasattr(st.session_state.game, 'logger'):
            game_history = st.session_state.game.logger.game_history
            
            # Filter for move entries
            moves = [entry for entry in game_history if 'move' in entry]
            
            if moves:
                for move in moves[-10:]:  # Show last 10 moves
                    status_icon = "✅" if move.get('is_valid', True) else "❌"
                    with st.expander(f"{status_icon} Move {move['move_number']} - {move['player'].upper()}"):
                        st.write(f"**Move:** {move['move']}")
                        st.write(f"**Reasoning:** {move['reasoning']}")
                        st.write(f"**Time:** {move['timestamp']}")
            else:
                st.info("No moves yet")
        
        # Game statistics
        if st.session_state.game_history:
            st.subheader("🏆 Game Results")
            for i, result in enumerate(st.session_state.game_history):
                st.write(f"**Game {i+1}:** {result['result']}")
                if result.get('winner'):
                    st.write(f"  Winner: {result['winner']}")
                st.write(f"  Moves: {result['total_moves']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Players of Games - AI vs AI Game Arena")
    parser.add_argument(
        '--game', 
        choices=['chess', 'tictactoe'], 
        default='chess',
        help='Type of game to play'
    )
    parser.add_argument(
        '--player1', 
        choices=['grok', 'claude'], 
        default='grok',
        help='Model for player 1'
    )
    parser.add_argument(
        '--player2', 
        choices=['grok', 'claude'], 
        default='claude',
        help='Model for player 2'
    )
    parser.add_argument(
        '--num-games', 
        type=int, 
        default=1,
        help='Number of games to play'
    )
    parser.add_argument(
        '--web', 
        action='store_true',
        help='Run Streamlit web interface'
    )
    parser.add_argument(
        '--no-log', 
        action='store_true',
        help='Disable logging to file'
    )
    
    args = parser.parse_args()
    
    # Validate API keys
    if not validate_api_keys():
        sys.exit(1)
    
    if args.web:
        # Run Streamlit app
        print("🌐 Starting Streamlit web interface...")
        print("The web interface should open automatically in your browser.")
        print("If not, navigate to: http://localhost:8501")
        run_streamlit_app()
    else:
        # Run console mode
        try:
            results = run_console_game(
                game_type=args.game,
                player1=args.player1,
                player2=args.player2,
                num_games=args.num_games,
                log_to_file=not args.no_log
            )
        except KeyboardInterrupt:
            print("\n\n⏹️  Game interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
