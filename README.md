Hanto Tournament Visualizer
===========================

Visualizes output of the Hanto game runner for CS 4233.

## Requirements

- Python>=2.7<3.0
- Tk
- PIL

## Example Usage

### Single Game

    java -classpath ./Hanto.jar:./studentsmin.jar:./studentsmin.jar hanto.tournament.TournamentRunner hanto.studentsmin.tournament.HantoPlayer hanto.studentsmin.tournament.HantoPlayer | python hanto.py --delay 500

### Multiple Games

	java ... >> game_output
	java ... >> game_output
	java ... >> game_output
	java ... >> game_output
    cat "game_output" | python hanto.py --continuous --fullscreen