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
    from error_logger import error_logger, log_error, log_warning, log_info, ErrorCategory, ErrorLevel
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
    
    # Initialize session state for debug outputs
    if 'debug_outputs' not in st.session_state:
        st.session_state.debug_outputs = []
    
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
                log_info("Testing API connections", ErrorCategory.API_ERROR)
                from api_utils import call_grok, call_claude
                
                # Test Grok
                log_info("Testing Grok API", ErrorCategory.API_ERROR, {"model": config.GROK_MODEL})
                grok_result = call_grok("Test", config.GROK_API_KEY, config.GROK_MODEL)
                if grok_result:
                    st.sidebar.success(f"✅ Grok API working ({config.GROK_MODEL}): {grok_result[:20]}...")
                    log_info("Grok API test successful", ErrorCategory.API_ERROR, {"response_length": len(grok_result)})
                else:
                    st.sidebar.error("❌ Grok API failed - check server logs")
                    log_error("Grok API test failed - no response", ErrorCategory.API_ERROR, {"model": config.GROK_MODEL})
                
                # Test Claude  
                log_info("Testing Claude API", ErrorCategory.API_ERROR, {"model": config.CLAUDE_MODEL})
                claude_result = call_claude("Test", config.CLAUDE_API_KEY, config.CLAUDE_MODEL)
                if claude_result:
                    st.sidebar.success(f"✅ Claude API working: {claude_result[:20]}...")
                    log_info("Claude API test successful", ErrorCategory.API_ERROR, {"response_length": len(claude_result)})
                else:
                    st.sidebar.error("❌ Claude API failed - check server logs")
                    log_error("Claude API test failed - no response", ErrorCategory.API_ERROR, {"model": config.CLAUDE_MODEL})
                    
            except Exception as e:
                st.sidebar.error(f"❌ API test failed: {e}")
                log_error("API test exception", ErrorCategory.API_ERROR, {"error": str(e)}, e)
    
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
                st.session_state.last_button_press = f"Next Move at {datetime.now().strftime('%H:%M:%S')}"
                st.rerun()
    
    with col3:
        if st.button("⏩ Auto Play"):
            st.session_state.auto_play = not st.session_state.get('auto_play', False)
            st.session_state.last_button_press = f"Auto Play {'ON' if st.session_state.auto_play else 'OFF'} at {datetime.now().strftime('%H:%M:%S')}"
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
            log_info("Starting new chess game", ErrorCategory.GAME_LOGIC, {"players": {"player1": "grok", "player2": "claude"}})
            players = {'player1': 'grok', 'player2': 'claude'}
            st.session_state.game = ChessGame(players, log_to_file=False)
            st.success("✅ New chess game started!")
            log_info("Chess game created successfully", ErrorCategory.GAME_LOGIC)
        except Exception as e:
            st.error(f"❌ Failed to create game: {e}")
            log_error("Failed to create chess game", ErrorCategory.GAME_LOGIC, {"error": str(e)}, e)
    
    # Display game if it exists
    if 'game' in st.session_state:
        game = st.session_state.game
        
        # Make move if requested
        if st.session_state.get('make_move', False):
            st.session_state.make_move = False
            
            # DEBUG: Add to session state immediately to confirm this code path is taken
            debug_entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "player": game.current_player,
                "move_count": game.move_count,
                "success": False,  # Will update this later
                "debug_output": "MOVE ATTEMPT STARTED - Debug capture initiated"
            }
            st.session_state.debug_outputs.append(debug_entry)
            
            try:
                log_info("Making AI move", ErrorCategory.GAME_LOGIC, {
                    "current_player": game.current_player,
                    "move_count": game.move_count,
                    "board_fen": game.board.fen()
                })
                with st.spinner("AI is thinking..."):
                    # Capture console output for debugging
                    import io
                    import sys
                    from contextlib import redirect_stdout, redirect_stderr
                    
                    debug_output = io.StringIO()
                    with redirect_stdout(debug_output), redirect_stderr(debug_output):
                        success = game.make_move()
                    
                    # Show debug output in expandable section
                    debug_text = debug_output.getvalue()
                    
                    # ALWAYS save debug output to session state - even if empty
                    debug_entry = {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "player": game.current_player,
                        "move_count": game.move_count,
                        "success": success,
                        "debug_output": debug_text if debug_text.strip() else f"No debug output captured for move attempt (success: {success})"
                    }
                    st.session_state.debug_outputs.append(debug_entry)
                    
                    # Keep only last 10 debug outputs
                    if len(st.session_state.debug_outputs) > 10:
                        st.session_state.debug_outputs = st.session_state.debug_outputs[-10:]
                    
                    # Show debug output if we have it
                    if debug_text.strip():
                        with st.expander("🔍 Debug Output (Move Validation Details)", expanded=not success):
                            # Show debug output in a text area for easy copying
                            st.text_area(
                                "Full Debug Output - Select All (Ctrl+A) and Copy (Ctrl+C)",
                                value=debug_text,
                                height=300,
                                key=f"main_debug_{game.move_count}",
                                help="This is the complete debug output - select all and copy to share"
                            )
                            
                        # Also save to error logger if failed
                        if not success:
                            log_error("Move validation failed with debug output", ErrorCategory.VALIDATION, {
                                "current_player": game.current_player,
                                "move_count": game.move_count,
                                "full_debug_output": debug_text
                            })
                    else:
                        # Show info about missing debug output
                        if not success:
                            st.warning("⚠️ Move failed but no debug output was captured. This suggests the validation isn't going through our debug system.")
                    
                    if not success:
                        st.error("❌ Move failed - Check debug output above for details")
                        log_error("AI move failed", ErrorCategory.GAME_LOGIC, {
                            "current_player": game.current_player,
                            "move_count": game.move_count,
                            "debug_output": debug_text[:500]  # First 500 chars
                        })
                    else:
                        st.success("✅ Move completed")
                        log_info("AI move completed successfully", ErrorCategory.GAME_LOGIC, {
                            "current_player": game.current_player,
                            "move_count": game.move_count
                        })
            except Exception as e:
                st.error(f"❌ Move error: {e}")
                log_error("Exception during AI move", ErrorCategory.GAME_LOGIC, {
                    "current_player": getattr(game, 'current_player', 'unknown'),
                    "error": str(e)
                }, e)
        
        # Display board
        try:
            # Create proper player mapping for the renderer (it expects 'white' and 'black' keys)
            player_names = {
                'white': 'White (Grok)', 
                'black': 'Black (Claude)'
            }
            
            # Get the last move for highlighting
            last_move = None
            if game.board.move_stack:  # Check if any moves have been made
                last_move = game.board.move_stack[-1]  # Get the most recent move
            
            board_html = chess_board_renderer.render_chess_board_with_info(
                game.board, 
                player_names,
                highlight_squares=None,
                last_move=last_move
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
        
        # Game log - Enhanced to show complete game history
        st.subheader("📝 Complete Game Log")
        try:
            # Access the game history directly from the logger
            if hasattr(game.logger, 'game_history'):
                log_entries = game.logger.game_history
                if log_entries:
                    # Show recent activity summary
                    if len(log_entries) > 0:
                        last_entry = log_entries[-1]
                        last_player = "Grok" if last_entry.get('player') == "player1" else "Claude"
                        last_move = last_entry.get('move', 'Unknown')
                        last_time = ""
                        if last_entry.get('timestamp'):
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(last_entry['timestamp'].replace('Z', '+00:00'))
                                last_time = dt.strftime("%H:%M:%S")
                            except:
                                pass
                        
                        st.info(f"🎯 **Latest Move:** {last_player} played `{last_move}` at {last_time}")
                    
                    # Create a scrollable container for the complete game log
                    log_container = st.container()
                    with log_container:
                        st.markdown("**📚 Complete Game History:**")
                        st.markdown("*Click on any move to see detailed AI reasoning*")
                        
                        # Show ALL moves, not just the last 5
                        for entry in log_entries:
                            if isinstance(entry, dict) and 'move' in entry:
                                status = "✅" if entry.get('is_valid', True) else "❌"
                                move = entry.get('move', 'Unknown')
                                reasoning = entry.get('reasoning', 'No reasoning')
                                player = entry.get('player', 'Unknown')
                                move_num = entry.get('move_number', '?')
                                timestamp = entry.get('timestamp', '')
                                game_state = entry.get('game_state', '')
                                
                                # Format timestamp to show just time
                                time_str = ""
                                if timestamp:
                                    try:
                                        from datetime import datetime
                                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                        time_str = dt.strftime("%H:%M:%S")
                                    except:
                                        time_str = timestamp[-8:] if len(timestamp) > 8 else timestamp
                                
                                # Player color indicator and styling
                                if player == "player1":
                                    player_color = "🤖"
                                    player_name = "Grok"
                                    player_style = "color: #2E86C1;"  # Blue for Grok
                                else:
                                    player_color = "🧠"
                                    player_name = "Claude"
                                    player_style = "color: #A569BD;"  # Purple for Claude
                                
                                # Create an expandable section for each move
                                with st.expander(f"{status} Move {move_num} - {player_color} {player_name}: {move} ({time_str})", expanded=(move_num == len(log_entries))):
                                    # Move details in a nice format
                                    col1, col2 = st.columns([1, 3])
                                    
                                    with col1:
                                        st.markdown(f"**Player:** <span style='{player_style}'>{player_name}</span>", unsafe_allow_html=True)
                                        st.markdown(f"**Move:** `{move}`")
                                        st.markdown(f"**Time:** {time_str}")
                                        st.markdown(f"**Valid:** {'Yes' if entry.get('is_valid', True) else 'No'}")
                                    
                                    with col2:
                                        st.markdown("**AI Reasoning & Strategy:**")
                                        # Show more reasoning (up to 500 characters for detailed view)
                                        if len(reasoning) > 500:
                                            reasoning_short = reasoning[:200] + "..."
                                            reasoning_full = reasoning
                                            st.markdown(reasoning_short)
                                            
                                            if st.button(f"Show Full Reasoning", key=f"full_reasoning_{move_num}"):
                                                st.markdown("**Full Reasoning:**")
                                                st.markdown(reasoning_full)
                                        else:
                                            st.markdown(reasoning)
                                    
                                    # Show additional context if available
                                    if game_state:
                                        with st.expander("🔍 Technical Details", expanded=False):
                                            st.text(f"Board State (FEN): {game_state}")
                                
                                # Add spacing between moves
                                st.markdown("")
                        
                        # Show game statistics
                        total_moves = len(log_entries)
                        valid_moves = len([e for e in log_entries if e.get('is_valid', True)])
                        invalid_moves = total_moves - valid_moves
                        
                        st.markdown(f"**Game Stats:** {total_moves} total moves | {valid_moves} valid | {invalid_moves} invalid")
                        
                else:
                    st.info("🎮 No moves yet - click 'Next Move' to start the game!")
                    st.markdown("The complete game history will appear here as moves are made.")
            else:
                st.warning("Game log not available - moves will appear here when the game starts")
        except Exception as e:
            st.error(f"Game log error: {e}")
            st.text("Moves will appear here when the game starts")
            log_error("Game log display error", ErrorCategory.UI_ERROR, {"error": str(e)}, e)
    
    # Error Log Viewer
    st.sidebar.subheader("🐛 Error & Bug Log")
    
    # Error log controls
    with st.sidebar.expander("📊 Error Summary", expanded=True):
        try:
            summary = error_logger.get_error_summary()
            st.write(f"**Session**: {summary['session_id']}")
            st.write(f"**Total Logs**: {summary['total_logs']}")
            
            # Show level counts
            if summary['level_counts']:
                st.write("**By Level:**")
                for level, count in summary['level_counts'].items():
                    emoji = {"ERROR": "🔴", "WARNING": "🟡", "INFO": "🔵", "DEBUG": "⚪", "CRITICAL": "🟣"}.get(level, "⚫")
                    st.write(f"{emoji} {level}: {count}")
            
            # Show category counts
            if summary['category_counts']:
                st.write("**By Category:**")
                for category, count in list(summary['category_counts'].items())[:3]:  # Top 3
                    st.write(f"• {category}: {count}")
        except Exception as e:
            st.sidebar.error(f"Error summary failed: {e}")
    
    # Error log viewer
    with st.sidebar.expander("📋 Recent Errors", expanded=False):
        try:
            # Filter controls
            level_filter = st.selectbox("Filter by Level", 
                                      ["All"] + [level.value for level in ErrorLevel],
                                      key="error_level_filter")
            
            category_filter = st.selectbox("Filter by Category",
                                         ["All"] + [cat.value for cat in ErrorCategory],
                                         key="error_category_filter")
            
            # Get filtered logs
            level_enum = None if level_filter == "All" else ErrorLevel(level_filter)
            category_enum = None if category_filter == "All" else ErrorCategory(category_filter)
            
            logs = error_logger.get_logs(level_enum, category_enum, last_n=10)
            
            if logs:
                for log in logs[-5:]:  # Show last 5
                    timestamp = log['timestamp'][11:19]  # Just time
                    level = log['level']
                    message = log['message'][:40] + "..." if len(log['message']) > 40 else log['message']
                    
                    emoji = {"ERROR": "🔴", "WARNING": "🟡", "INFO": "🔵", "DEBUG": "⚪", "CRITICAL": "🟣"}.get(level, "⚫")
                    st.text(f"{emoji} [{timestamp}] {message}")
            else:
                st.text("No logs matching filter")
        except Exception as e:
            st.sidebar.error(f"Error log viewer failed: {e}")
    
    # Debug output viewer - Always expanded for easy access
    with st.sidebar.expander("🔍 Debug Output (Copy/Paste Here)", expanded=True):
        try:
            # Get debug outputs from session state
            debug_outputs = st.session_state.get('debug_outputs', [])
            
            # DIAGNOSTIC INFO - Show what's in session state
            st.markdown(f"**🔧 Debug Diagnostics:**")
            st.text(f"Session debug_outputs length: {len(debug_outputs)}")
            st.text(f"Game exists: {'game' in st.session_state}")
            if 'game' in st.session_state:
                st.text(f"Game move count: {st.session_state.game.move_count}")
            st.text(f"Make move button pressed: {st.session_state.get('make_move', False)}")
            st.text(f"Auto play enabled: {st.session_state.get('auto_play', False)}")
            
            # Show recent button presses
            if hasattr(st.session_state, 'last_button_press'):
                st.text(f"Last button: {st.session_state.last_button_press}")
            
            # Filter for failed moves only
            failed_debug_outputs = [d for d in debug_outputs if not d['success']]
            
            if failed_debug_outputs:
                st.markdown("**📋 Copy any debug output below:**")
                st.markdown(f"*Found {len(failed_debug_outputs)} validation failures*")
                
                for i, debug_entry in enumerate(reversed(failed_debug_outputs[-5:])):  # Last 5, newest first
                    timestamp = debug_entry['timestamp']
                    player = debug_entry['player']
                    move_count = debug_entry['move_count']
                    debug_output = debug_entry['debug_output']
                    
                    st.markdown(f"**🚨 Move {move_count} - {player} [{timestamp}]:**")
                    
                    # Show the full debug output in a text area for easy copying
                    st.text_area(
                        f"Debug Output {i+1}",
                        value=debug_output,
                        height=200,
                        key=f"session_debug_{i}_{move_count}",
                        help="Select all (Ctrl+A) and copy (Ctrl+C) to share this debug output"
                    )
                    
                    st.markdown("---")  # Separator
            else:
                # Check if we have any debug outputs at all
                all_debug_outputs = st.session_state.get('debug_outputs', [])
                if all_debug_outputs:
                    st.info(f"🎯 **{len(all_debug_outputs)} moves processed, but no validation failures detected**")
                    
                    # Show recent moves for debugging
                    st.markdown("**🔍 All Recent Move Attempts:**")
                    for i, entry in enumerate(reversed(all_debug_outputs[-5:])):
                        status = "✅ Success" if entry['success'] else "❌ Failed"
                        st.text(f"Move {entry['move_count']} - {entry['player']}: {status}")
                        st.text(f"  Time: {entry['timestamp']}")
                        st.text(f"  Debug chars: {len(entry['debug_output'])}")
                        
                        # Show a preview of debug output for failed moves
                        if not entry['success'] and entry['debug_output']:
                            st.text_area(
                                f"Failed Move {entry['move_count']} Debug",
                                value=entry['debug_output'][:500] + "..." if len(entry['debug_output']) > 500 else entry['debug_output'],
                                height=100,
                                key=f"failed_preview_{i}_{entry['move_count']}"
                            )
                        st.markdown("---")
                else:
                    st.info("🎯 **No moves attempted yet**\n\nClick 'Next Move' to make a move and see debug info here.")
        except Exception as e:
            st.error(f"Debug viewer error: {e}")
    
    # Export and clear controls
    with st.sidebar.expander("🔧 Log Management", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Show All Logs"):
                try:
                    all_logs = error_logger.get_logs()
                    if all_logs:
                        # Show all logs in a text area for copying
                        logs_text = "\n".join([
                            f"[{log['timestamp']}] {log['level']} - {log['category']}: {log['message']}"
                            for log in all_logs[-10:]  # Last 10 logs
                        ])
                        st.text_area("Recent Logs (Copy/Paste)", value=logs_text, height=200, key="all_logs_display")
                    else:
                        st.info("No logs available")
                except Exception as e:
                    st.error(f"Show logs failed: {e}")
        
        with col2:
            if st.button("🗑️ Clear Logs"):
                try:
                    error_logger.clear_logs()
                    st.success("Logs cleared!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Clear failed: {e}")
    
    # Debug console (simplified)
    st.sidebar.subheader("🖥️ Debug Console")
    try:
        from debug_console import debug_console
        messages = list(debug_console.messages)
        if messages:
            for msg in messages[-3:]:  # Show last 3 debug messages
                st.sidebar.text(f"[{msg['timestamp']}] {msg['message'][:40]}...")
        else:
            st.sidebar.text("No debug messages")
    except Exception as e:
        st.sidebar.error(f"Debug error: {e}")
        log_error("Debug console error", ErrorCategory.UI_ERROR, {"error": str(e)}, e)

if __name__ == "__main__":
    main()
