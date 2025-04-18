from flask import Flask, render_template, request, redirect, url_for, session
import random

app = Flask(__name__)
app.secret_key = 'secretkey'  # Needed for session management

# Constants
NUM_TILES = 30
SPECIAL_TILE_CHANCE = 0.5
TILE_TYPES = ['normal', 'trivia', 'monster', 'chance']
COLORS = ['red', 'green', 'yellow', 'blue']

# Sample trivia categories and questions
TRIVIA_CATEGORIES = {
    'general': [
        {"question": "What is the capital of France?", "answer": "Paris"},
        {"question": "What is 5 + 7?", "answer": "12"},
    ],
    'science': [
        {"question": "What planet is known as the Red Planet?", "answer": "Mars"},
        {"question": "What gas do plants absorb from the atmosphere?", "answer": "Carbon Dioxide"},
    ],
    'pop_culture': [
        {"question": "Who played Iron Man in the Marvel movies?", "answer": "Robert Downey Jr."},
        {"question": "What year did the first Harry Potter movie come out?", "answer": "2001"},
    ]
}

# Board state initialization
def determine_tile():
    board = []
    for _ in range(NUM_TILES):
        if random.random() < SPECIAL_TILE_CHANCE:
            board.append(random.choice(TILE_TYPES[1:]))
        else:
            board.append('normal')
    return board

# Dice roll function
def roll_dice():
    return random.randint(1, 6)

# Check if player is stuck on trivia tile
def is_stuck(player):
    return session['players'][player].get('stuck', False)

# Offer path choice placeholder
# In this prototype, we simplify pathing

def offer_choice():
    return random.choice(['path1', 'path2'])

# Handle trivia question

def trivia():
    category = random.choice(list(TRIVIA_CATEGORIES.keys()))
    question = random.choice(TRIVIA_CATEGORIES[category])
    return {"category": category, "question": question['question'], "answer": question['answer']}

# Move player

def move_player(color, steps):
    players = session['players']
    players[color]['position'] += steps
    if players[color]['position'] >= NUM_TILES:
        players[color]['position'] = NUM_TILES - 1
    session['players'] = players

# Setup route to initialize game
@app.route('/')
def index():
    session['board'] = determine_tile()
    session['players'] = {
        color: {'position': 0, 'stuck': False, 'trivia_wins': 0, 'monster_wins': 0} for color in COLORS
    }
    session['turn'] = 0
    session['winner'] = None
    return redirect(url_for('game'))

@app.route('/game', methods=['GET', 'POST'])
def game():
    board = session['board']
    players = session['players']
    turn = session['turn']
    color = COLORS[turn % 4]
    message = ""

    # Check for winner
    for p_color, p_data in players.items():
        if p_data['position'] == NUM_TILES - 1:
            session['winner'] = p_color
            return redirect(url_for('winner'))

    if request.method == 'POST':
        if is_stuck(color):
            q = session.get('trivia_q')
            answer = request.form['answer'].strip()
            if q and answer.lower() == q['answer'].lower():
                players[color]['stuck'] = False
                players[color]['trivia_wins'] += 1
                message = f"Correct! You're free to move next turn."
            else:
                message = f"Wrong! You're still stuck."
            session['players'] = players
        else:
            roll = roll_dice()
            move_player(color, roll)
            position = players[color]['position']

            # Duel check
            for other_color, other_data in players.items():
                if other_color != color and other_data['position'] == position:
                    p_roll = roll_dice()
                    o_roll = roll_dice()
                    if p_roll > o_roll:
                        move_player(color, 3)
                        players[other_color]['position'] = max(0, players[other_color]['position'] - 2)
                        message += f" Duel! {color} wins and moves forward 3. {other_color} moves back 2."
                    elif o_roll > p_roll:
                        move_player(other_color, 3)
                        players[color]['position'] = max(0, players[color]['position'] - 2)
                        message += f" Duel! {other_color} wins and moves forward 3. {color} moves back 2."
                    else:
                        message += f" Duel! It's a tie. No one moves."

            tile = board[position]

            if tile == 'trivia':
                players[color]['stuck'] = True
                session['trivia_q'] = trivia()
                message += f" Trivia time! ({session['trivia_q']['category'].capitalize()}) {session['trivia_q']['question']}"
            elif tile == 'monster':
                player_roll = roll_dice()
                monster_roll = roll_dice()
                if player_roll >= monster_roll:
                    players[color]['monster_wins'] += 1
                    message += " You defeated the monster!"
                else:
                    players[color]['position'] = max(0, players[color]['position'] - 2)
                    message += " You lost to the monster and moved back 2 spaces."
            elif tile == 'chance':
                chance_roll = roll_dice()
                if chance_roll % 2 == 0:
                    move_player(color, chance_roll)
                    message += f" Chance roll: {chance_roll}. You moved forward!"
                else:
                    players[color]['position'] = max(0, players[color]['position'] - chance_roll)
                    message += f" Chance roll: {chance_roll}. You moved backward!"
            else:
                message += f" Landed on a normal tile."

            session['players'] = players
            session['trivia_q'] = None

        session['turn'] += 1
        return redirect(url_for('game'))

    current_question = session.get('trivia_q')
    return render_template('game.html', board=board, players=players, turn=turn, color=color, message=message, question=current_question)

@app.route('/winner')
def winner():
    return render_template('winner.html', color=session.get('winner'))

if __name__ == '__main__':
    app.run(debug=True)
