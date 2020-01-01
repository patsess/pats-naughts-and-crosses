
import os
import logging
import time
import random
from copy import deepcopy
from flask import Flask, request, session, render_template

__author__ = 'psessford'

logging.basicConfig(level=logging.INFO)

"""
note: for details on deploying using Heroku, see 
https://stackabuse.com/deploying-a-flask-application-to-heroku/

note: for information on Flask sessions, see 'Sessions' section of 
https://flask.palletsprojects.com/en/0.12.x/quickstart/#sessions
"""


app = Flask(__name__)


@app.route('/')
def get_game_page():
    if 'game_board' not in session:
        _initialise_game()

    return _get_game_rendered_template()


@app.route('/', methods=['POST'])
def get_game_page_post():
    is_reset_requested = _is_reset_requested()
    if 'game_board' not in session or is_reset_requested:
        _initialise_game()
        if is_reset_requested:
            return get_game_page()

    if session['winner_msg'] is not None:
        return _get_game_rendered_template(winning_msg=session['winner_msg'])

    player_game_move = _get_player_game_move()
    if player_game_move is None:
        error_msg_ = ('unrecognised move, looking for an integer from the '
                      'spaces available')
        return _get_game_rendered_template(error_msg=error_msg_)

    player_move_coords = _handle_player_game_move(move=player_game_move)
    if player_move_coords is None:
        return _get_game_rendered_template(error_msg='cannot move there')

    session['game_board'][player_move_coords[0]][player_move_coords[1]] = 'X'
    if _game_has_winner(wanted_str='X', game_board=session['game_board']):
        session['winner_msg'] = 'CONGRATULATIONS, YOU WON!!'
        return _get_game_rendered_template(winning_msg=session['winner_msg'])

    ai_game_move = _make_ai_game_move()
    if _make_ai_game_move is None:
        session['winner_msg'] = 'A DRAW!!'
        return _get_game_rendered_template(winning_msg=session['winner_msg'])

    if _game_has_winner(wanted_str='O', game_board=session['game_board']):
        session['winner_msg'] = 'OH NO, YOU LOST!!'
        return _get_game_rendered_template(winning_msg=session['winner_msg'])

    game_moves = (player_game_move, ai_game_move)
    session['game_move_history'] += [game_moves]

    return _get_game_rendered_template()


# app.secret_key = os.urandom(24)  # has problems when deployed with Heroku
app.secret_key = (
    '\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8')


def _get_game_rendered_template(error_msg=None, winning_msg=None):
    assert not (error_msg is not None and winning_msg is not None)

    if error_msg is not None and winning_msg is None:
        return render_template(
            'game.html',
            game_board=_get_string_converted_board(),
            game_move_history=session['game_move_history'],
            error_msg=error_msg)
    elif error_msg is None and winning_msg is not None:
        return render_template(
            'game.html',
            game_board=_get_string_converted_board(),
            game_move_history=session['game_move_history'],
            winning_msg=winning_msg)
    else:
        return render_template(
            'game.html',
            game_board=_get_string_converted_board(),
            game_move_history=session['game_move_history'])


def _is_reset_requested():
    player_game_move = request.form.get('player_game_move')
    return (player_game_move is not None and player_game_move.lower() == 'r')


def _initialise_game():
    session['game_board'] = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    session['game_move_history'] = []
    session['winner_msg'] = None


def _get_player_game_move():
    player_game_move = request.form['player_game_move']
    try:
        player_game_move = int(player_game_move)
    except:
        return None

    return player_game_move


def _handle_player_game_move(move):
    assert isinstance(move, int)
    available_moves = _get_available_board_spaces()
    if move not in available_moves:
        return None

    board_coords = _get_board_coordinates(space_int=move)
    # current_value = session['game_board'][board_coords[0]][board_coords[1]]
    return board_coords


def _get_board_coordinates(space_int):
    n_rows = 3
    n_cols = 3
    board_row_index = (space_int - 1) // n_cols
    board_col_index = (space_int - 1) % n_rows
    return board_row_index, board_col_index


def _make_ai_game_move():
    time.sleep(0.5)  # pause before AI moves
    available_moves = _get_available_board_spaces()
    if len(available_moves) == 0:
        return None

    winning_ai_move = _look_for_winning_move(
        available_moves=available_moves, wanted_str='O')
    winning_player_move = _look_for_winning_move(
        available_moves=available_moves, wanted_str='X')
    print(winning_ai_move, winning_player_move)

    if winning_ai_move is not None:
        move = winning_ai_move
    elif winning_player_move is not None:
        move = winning_player_move
    elif 5 in available_moves:
        move = 5  # take the centre if it's available
    else:
        move = random.choice(available_moves)

    board_coords = _get_board_coordinates(space_int=move)
    session['game_board'][board_coords[0]][board_coords[1]] = 'O'
    return move


def _get_available_board_spaces():
    return [
        s for row in session['game_board'] for s in row if isinstance(s, int)]


def _look_for_winning_move(available_moves, wanted_str):
    for possible_move in available_moves:
        poss_game_board = deepcopy(session['game_board'])
        poss_board_coords = _get_board_coordinates(space_int=possible_move)
        poss_game_board[
            poss_board_coords[0]][poss_board_coords[1]] = wanted_str
        if _game_has_winner(wanted_str=wanted_str, game_board=poss_game_board):
            return possible_move

    return None


def _get_string_converted_board():
    return [' | '.join([str(s) for s in row]) for row in session['game_board']]


def _game_has_winner(wanted_str, game_board):
    assert isinstance(wanted_str, str)
    assert (wanted_str in ('X', 'O'))

    def _is_wanted(space_):
        return isinstance(space_, str) and space_ == wanted_str

    for row in game_board:
        if all(_is_wanted(s) for s in row):
            return True

    assert (len(set(len(row) for row in game_board)) == 1)
    n_cols = len(game_board[0])
    for col_index in range(n_cols):
        if all(_is_wanted(row[col_index]) for row in game_board):
            return True

    if all(_is_wanted(game_board[row][col])
           for row, col in [(i, i) for i in range(n_cols)]):
        return True

    if all(_is_wanted(game_board[row][col])
           for row, col in [(i, n_cols - 1 - i) for i in range(n_cols)]):
        return True

    return False


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
