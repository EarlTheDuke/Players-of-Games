"""Beautiful chess board renderer for Streamlit using HTML/CSS."""
import chess
import streamlit as st

# Unicode chess pieces
PIECE_SYMBOLS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',  # White pieces
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'   # Black pieces
}

def render_chess_board_with_info(board: chess.Board, player_info=None, highlight_squares=None, last_move=None, board_size=400):
    """
    Render a beautiful chess board with player info and captured pieces.
    
    Args:
        board: python-chess Board object
        player_info: Dict with player names and colors {'white': 'Player1', 'black': 'Player2'}
        highlight_squares: List of squares to highlight (e.g., ['e4', 'e5'])
        last_move: Last move made (chess.Move object) - will be highlighted in yellow
        board_size: Size of the board in pixels
    
    Returns:
        HTML string for the chess board with player info
    """
    if player_info is None:
        player_info = {'white': 'White', 'black': 'Black'}
    
    # Get captured pieces
    captured_pieces = get_captured_pieces(board)
    
    # Add last move squares to highlight_squares for yellow highlighting
    combined_highlights = highlight_squares[:] if highlight_squares else []
    if last_move:
        # Add from and to squares of the last move for yellow highlighting
        from_square = chess.square_name(last_move.from_square)
        to_square = chess.square_name(last_move.to_square)
        combined_highlights.extend([from_square, to_square])
    
    # Generate the basic board HTML
    board_html = render_chess_board(board, combined_highlights, board_size)
    
    # Add player info and captured pieces panel
    info_panel_width = 220  # Slightly wider to show all captured units and scores
    total_width = board_size + info_panel_width + 15  # Reduced spacing
    
    # Running totals for captured pieces (points)
    black_captured_score = calculate_captured_score(captured_pieces['white'])  # Points for Black
    white_captured_score = calculate_captured_score(captured_pieces['black'])  # Points for White
    
    info_panel_html = f"""
    <div style="width: 100%; max-width: {total_width}px; margin: 0; overflow: visible;">
        <div style="display: flex; gap: 15px; align-items: flex-start;">
            <div style="flex: 0 0 {board_size}px;">
                {board_html}
            </div>
            <div style="flex: 0 0 {info_panel_width}px; background: #F0D9B5; border: 3px solid #8B4513; border-radius: 8px; padding: 12px; font-family: Arial, sans-serif; box-sizing: border-box; margin-top: 3px;">
            <!-- Black Player Info (Top) -->
            <div style="margin-bottom: 20px; text-align: center;">
                <div style="background: #2C2C2C; color: white; padding: 8px; border-radius: 5px; margin-bottom: 10px;">
                    <strong>♛ {player_info.get('black', 'Black')}</strong>
                </div>
                <div style="background: #E8E8E8; padding: 8px; border-radius: 5px; min-height: 40px;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Captured: <span style=\"font-weight: bold; color: #333;\">{black_captured_score}</span> pts</div>
                    <div style="font-size: 18px; line-height: 1.2; word-break: break-word; overflow-wrap: anywhere;">
                        {format_captured_pieces(captured_pieces['white'])}
                    </div>
                </div>
            </div>
            
            <!-- Game Status -->
            <div style="text-align: center; margin: 20px 0; padding: 10px; background: #D2B48C; border-radius: 5px;">
                <div style="font-size: 12px; color: #8B4513;">Turn:</div>
                <div style="font-weight: bold; color: #8B4513;">
                    {'White' if board.turn == chess.WHITE else 'Black'}
                </div>
                <div style="font-size: 12px; color: #8B4513; margin-top: 5px;">
                    Move #{board.fullmove_number}
                </div>
            </div>
            
            <!-- White Player Info (Bottom) -->
            <div style="text-align: center;">
                <div style="background: #E8E8E8; padding: 8px; border-radius: 5px; min-height: 40px; margin-bottom: 10px;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Captured: <span style=\"font-weight: bold; color: #333;\">{white_captured_score}</span> pts</div>
                    <div style="font-size: 18px; line-height: 1.2; word-break: break-word; overflow-wrap: anywhere;">
                        {format_captured_pieces(captured_pieces['black'])}
                    </div>
                </div>
                <div style="background: #FFFFFF; color: #2C2C2C; padding: 8px; border-radius: 5px; border: 1px solid #CCC;">
                    <strong>♔ {player_info.get('white', 'White')}</strong>
                </div>
            </div>
        </div>
    </div>
    """
    
    return info_panel_html

def get_captured_pieces(board: chess.Board):
    """
    Calculate which pieces have been captured by analyzing the board.
    
    Args:
        board: python-chess Board object
    
    Returns:
        Dict with 'white' and 'black' keys containing lists of captured pieces
    """
    # Starting pieces count
    starting_pieces = {
        'white': {'P': 8, 'R': 2, 'N': 2, 'B': 2, 'Q': 1, 'K': 1},
        'black': {'p': 8, 'r': 2, 'n': 2, 'b': 2, 'q': 1, 'k': 1}
    }
    
    # Count current pieces on board
    current_pieces = {
        'white': {'P': 0, 'R': 0, 'N': 0, 'B': 0, 'Q': 0, 'K': 0},
        'black': {'p': 0, 'r': 0, 'n': 0, 'b': 0, 'q': 0, 'k': 0}
    }
    
    # Count pieces currently on the board
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            if piece.color == chess.WHITE:
                current_pieces['white'][piece.symbol().upper()] += 1
            else:
                current_pieces['black'][piece.symbol().lower()] += 1
    
    # Calculate captured pieces
    captured = {'white': [], 'black': []}
    
    # White pieces captured by Black
    for piece_type, starting_count in starting_pieces['white'].items():
        current_count = current_pieces['white'][piece_type]
        captured_count = starting_count - current_count
        for _ in range(captured_count):
            captured['white'].append(piece_type)
    
    # Black pieces captured by White  
    for piece_type, starting_count in starting_pieces['black'].items():
        current_count = current_pieces['black'][piece_type]
        captured_count = starting_count - current_count
        for _ in range(captured_count):
            captured['black'].append(piece_type)
    
    return captured

def format_captured_pieces(pieces_list):
    """
    Format a list of captured pieces as Unicode symbols.
    
    Args:
        pieces_list: List of piece symbols (e.g., ['P', 'N', 'q'])
    
    Returns:
        String of Unicode piece symbols
    """
    if not pieces_list:
        return "—"
    
    # Sort pieces by value (most valuable first)
    piece_order = {'Q': 0, 'q': 0, 'R': 1, 'r': 1, 'B': 2, 'b': 2, 'N': 3, 'n': 3, 'P': 4, 'p': 4}
    sorted_pieces = sorted(pieces_list, key=lambda x: piece_order.get(x, 5))
    
    # Convert to Unicode symbols
    symbols = []
    for piece in sorted_pieces:
        if piece.isupper():
            symbols.append(PIECE_SYMBOLS[piece])
        else:
            symbols.append(PIECE_SYMBOLS[piece])
    
    return ''.join(symbols)

def calculate_captured_score(pieces_list):
    """Calculate score for a list of captured pieces (material points)."""
    if not pieces_list:
        return 0
    values = {'P': 1, 'p': 1, 'N': 3, 'n': 3, 'B': 3, 'b': 3, 'R': 5, 'r': 5, 'Q': 9, 'q': 9, 'K': 0, 'k': 0}
    score = 0
    for p in pieces_list:
        score += values.get(p, 0)
    return score

def render_chess_board(board: chess.Board, highlight_squares=None, board_size=400):
    """
    Render a beautiful chess board using HTML/CSS.
    
    Args:
        board: python-chess Board object
        highlight_squares: List of squares to highlight (e.g., ['e4', 'e5'])
        board_size: Size of the board in pixels
    
    Returns:
        HTML string for the chess board
    """
    if highlight_squares is None:
        highlight_squares = []
    
    # Convert square names to indices if needed
    highlight_indices = []
    for square in highlight_squares:
        if isinstance(square, str):
            highlight_indices.append(chess.parse_square(square))
        else:
            highlight_indices.append(square)
    
    cell_size = board_size // 8
    
    # CSS styles for the chess board
    css = f"""
    <style>
    .chess-board {{
        display: grid;
        grid-template-columns: repeat(8, {cell_size}px);
        grid-template-rows: repeat(8, {cell_size}px);
        border: 3px solid #8B4513;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        margin: 20px auto;
        background: #D2B48C;
        font-family: 'Arial Unicode MS', sans-serif;
    }}
    
    .chess-square {{
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: {cell_size * 0.7}px;
        font-weight: bold;
        position: relative;
        user-select: none;
    }}
    
    .light-square {{
        background-color: #F0D9B5;
    }}
    
    .dark-square {{
        background-color: #B58863;
    }}
    
    .highlighted-square {{
        background-color: #FFD700 !important;
        box-shadow: inset 0 0 0 3px #FF6B35;
    }}
    
    .last-move-square {{
        background-color: #90EE90 !important;
        box-shadow: inset 0 0 0 2px #228B22;
    }}
    
    .chess-piece {{
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        transition: transform 0.1s;
    }}
    
    .chess-piece:hover {{
        transform: scale(1.1);
    }}
    
    .white-piece {{
        color: #FFFFFF;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }}
    
    .black-piece {{
        color: #2C2C2C;
        text-shadow: 1px 1px 2px rgba(255,255,255,0.3);
    }}
    
    .coordinate-label {{
        position: absolute;
        font-size: {cell_size * 0.2}px;
        font-weight: bold;
        color: rgba(0,0,0,0.6);
    }}
    
    .rank-label {{
        top: 2px;
        left: 2px;
    }}
    
    .file-label {{
        bottom: 2px;
        right: 2px;
    }}
    </style>
    """
    
    # Generate the HTML for the chess board
    html = css + '<div class="chess-board">\n'
    
    # Iterate through ranks (8 to 1) and files (a to h)
    for rank in range(8, 0, -1):  # 8, 7, 6, 5, 4, 3, 2, 1
        for file in range(8):  # 0, 1, 2, 3, 4, 5, 6, 7 (a-h)
            square_index = chess.square(file, rank - 1)
            square_name = chess.square_name(square_index)
            
            # Determine square color
            is_light = (rank + file) % 2 == 1
            square_class = "light-square" if is_light else "dark-square"
            
            # Check for highlighting
            if square_index in highlight_indices:
                square_class += " highlighted-square"
            
            # Get piece on this square
            piece = board.piece_at(square_index)
            piece_html = ""
            piece_class = ""
            
            if piece:
                piece_symbol = PIECE_SYMBOLS.get(piece.symbol(), piece.symbol())
                piece_class = "white-piece" if piece.color == chess.WHITE else "black-piece"
                piece_html = f'<span class="chess-piece {piece_class}">{piece_symbol}</span>'
            
            # Add coordinate labels for edge squares
            coord_html = ""
            if file == 0:  # a-file, show rank
                coord_html += f'<span class="coordinate-label rank-label">{rank}</span>'
            if rank == 1:  # 1st rank, show file
                file_letter = chr(ord('a') + file)
                coord_html += f'<span class="coordinate-label file-label">{file_letter}</span>'
            
            html += f'    <div class="chess-square {square_class}" data-square="{square_name}">\n'
            html += f'        {coord_html}\n'
            html += f'        {piece_html}\n'
            html += f'    </div>\n'
    
    html += '</div>\n'
    return html

def render_chess_board_with_moves(board: chess.Board, last_move=None, board_size=400):
    """
    Render chess board with last move highlighted.
    
    Args:
        board: python-chess Board object
        last_move: Last move made (chess.Move object)
        board_size: Size of the board in pixels
    """
    highlight_squares = []
    if last_move:
        highlight_squares = [last_move.from_square, last_move.to_square]
    
    return render_chess_board(board, highlight_squares, board_size)

def render_mini_chess_board(board: chess.Board, board_size=200):
    """Render a smaller chess board for compact display."""
    return render_chess_board(board, board_size=board_size)

# Example usage and testing
if __name__ == "__main__":
    # Test with a sample position
    board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
    html = render_chess_board(board, highlight_squares=['e2', 'e4'])
    print(html)
