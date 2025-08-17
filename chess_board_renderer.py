"""Beautiful chess board renderer for Streamlit using HTML/CSS."""
import chess
import streamlit as st

# Unicode chess pieces
PIECE_SYMBOLS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',  # White pieces
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'   # Black pieces
}

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
