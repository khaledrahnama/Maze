*This project has been created as part of the 42 curriculum by REPLACE_WITH_YOUR_42_LOGIN.*

# A-Maze-ing

## Description

A-Maze-ing generates mazes from a configuration file, writes them in the
subject's hexadecimal format and shows them in the terminal.

Two modes are available. With `PERFECT=True` the maze is *perfect*: exactly
one path exists between any two cells. With `PERFECT=False` the result is a
board for a Pac-Man-like game: fully connected, with open corners and centre,
at least two independent routes and almost no dead ends. In both modes the
maze contains a "42" drawn by fully closed cells, the outer border is closed,
neighbouring cells always agree about the wall between them, and no 3x3 area
is completely open.

The generation logic lives in a single reusable module, `mazegen.py`, so a
later project can install it with pip and build mazes without this
command-line program.

## Instructions

Requirements: Python 3.10 or later; no third-party package is needed to run
the program.

```sh
make run                 # python3 a_maze_ing.py config.txt
make run CONFIG=my.txt   # another configuration file
make lint                # flake8 and mypy with the required flags
make lint-strict         # flake8 and mypy --strict
make debug               # run under pdb
make clean               # remove caches and generated mazes
make build               # build mazegen-1.0.0-py3-none-any.whl and .tar.gz
```

While the program runs it displays the maze and offers: `1` regenerate a new
maze (the output file is rewritten), `2` show or hide the shortest path, `3`
change the wall colours, `4` colour the "42", `5` quit. Ending the input
(Ctrl+D) or interrupting (Ctrl+C) also quits cleanly.

Every error prints one `Error: ...` line and exits with the status 1: missing
or unreadable configuration file, a line that is not `KEY=VALUE`, a repeated
or missing key, a value that is not a number, coordinates outside the maze,
an entry equal to the exit, or an output file that cannot be written.

## Configuration file format

One `KEY=VALUE` pair per line. Everything after `#` is a comment, and blank
lines are ignored. Keys are case-sensitive and must not be repeated.

| Key | Meaning | Example | Mandatory |
| --- | --- | --- | --- |
| `WIDTH` | Number of columns, at least 2 | `WIDTH=20` | yes |
| `HEIGHT` | Number of rows, at least 2 | `HEIGHT=20` | yes |
| `ENTRY` | Entry cell `x,y`, inside the maze | `ENTRY=0,0` | yes |
| `EXIT` | Exit cell `x,y`, different from the entry | `EXIT=19,19` | yes |
| `OUTPUT_FILE` | File to write the maze into | `OUTPUT_FILE=maze.txt` | yes |
| `PERFECT` | `True` for one single path, `False` for a playable board | `PERFECT=True` | yes |
| `SEED` | Integer seed; the same seed rebuilds the same maze | `SEED=42` | no |

The default `config.txt` in this repository is a working example.

### Output file

One hexadecimal digit per cell, one row per line: bit 1 is the north wall,
2 east, 4 south, 8 west, and a bit set means the wall is closed (so `F` is a
fully closed cell and `9` has its north and west walls closed). After the
grid comes an empty line, then the entry, the exit and the shortest path
written with the letters `N`, `E`, `S`, `W`. Every line ends with `\n`.

## The algorithm, and why

The maze is carved with a **randomised depth-first search**, also called the
*recursive backtracker*, written with an explicit stack:

1. Start at the entry, mark it visited.
2. Look at the cell on top of the stack and list its unvisited neighbours.
3. If there are none, pop the stack (backtrack).
4. Otherwise pick one at random, open the wall between the two cells, mark it
   visited and push it.

Every cell except the first is visited exactly once, and each visit opens
exactly one wall, so the result has `cells - 1` openings and is connected:
a spanning tree. A tree has no cycle, which is exactly the definition of a
perfect maze, so `PERFECT=True` is satisfied by construction.

Why this algorithm: it is simple to implement correctly, runs in time
proportional to the number of cells, needs no extra data structure beyond a
stack and a visited set, and produces long winding corridors, which look
better than the short bushy branches of Prim's or Kruskal's algorithms.
Using an explicit stack instead of recursion avoids Python's recursion limit
on large mazes.

For `PERFECT=False` the tree is then *braided*: each dead end gets one more
wall opened, and further walls are opened until the board has at least two
independent loops. The number of independent loops is
`openings - (cells - 1)`, which is 0 for the perfect maze and grows by one
with every extra opening. Every candidate wall is rejected if opening it
would create a fully open 3x3 area.

The "42" is placed before carving: its cells are marked as visited, so the
carver never enters them and their four walls stay closed. The program tries
each possible position and keeps the first one that avoids the entry, the
exit, the corners and the centre, and still leaves every other cell
reachable. If the maze is too small, the motif is skipped and the program
says so.

The shortest path is found with a **breadth-first search** from the entry,
which visits cells in order of distance, so the first route reaching the exit
is a shortest one. Each cell remembers its predecessor and the direction
used, and the path is rebuilt backwards from the exit.

## What is reusable, and how

`mazegen.py` is the reusable module: it contains the single class
`MazeGenerator`, depends only on the standard library, and knows nothing
about configuration files or the terminal. It is packaged as
`mazegen-1.0.0-py3-none-any.whl` (and `.tar.gz`) at the root of this
repository, and can be rebuilt with `make build`.

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install ./mazegen-1.0.0-py3-none-any.whl
```

```python
from mazegen import MazeGenerator

maze = MazeGenerator(20, 15, entry=(0, 0), exit=(19, 14),
                     perfect=False, seed=42)   # custom parameters
grid = maze.generate()      # the structure: grid[y][x] holds the wall bits
path = maze.solve()         # a solution: "SSEEN..." using N/E/S/W
print(maze.render(show_path=True))             # an ASCII picture
maze.write("maze.txt")                         # the subject's file format
```

Accessing the structure: `maze.grid` is a list of rows, one integer per cell
whose bits say which walls are closed (1 north, 2 east, 4 south, 8 west);
`maze.blocked` holds the cells of the "42"; `maze.solve()` returns a shortest
solution. The in-memory structure uses the same wall encoding as the output
file.

## Resources

- Jamis Buck, *Maze Generation: Recursive Backtracking* and the other
  articles in the same series.
- Wikipedia: *Maze generation algorithm*, *Spanning tree*,
  *Breadth-first search*.
- Python documentation: `random.Random`, `collections.deque`, `dataclasses`,
  `typing`, PEP 257 (docstring conventions), PEP 8.
- Python Packaging User Guide: *Packaging Python Projects* (pyproject.toml,
  `python -m build`).
- choosealicense.com, for comparing the MIT and Apache-2.0 licences.

How AI was used: as an explainer and a reviewer, not as an author. It was
used to compare maze generation algorithms before choosing the recursive
backtracker, to explain how to express the 3x3 open-area rule and how to
count independent loops, and to review error handling, docstrings and the
packaging files. Every suggestion was re-implemented, tested with several
seeds and sizes, and checked with flake8 and mypy; the design decisions and
the final code are my own, and I can explain each part of them.

## Project management

Solo project. Planned in five stages, each committed separately:
configuration and error handling, generation and the output file, the
playable board, the terminal display and menu, then packaging and
documentation. The braiding stage took the longest, because removing dead
ends can create 3x3 open areas, which required undoing a change and trying
another wall. Tools used: flake8 and mypy for the standards, `make lint`
before every commit, and repeated runs with different seeds and sizes to
catch cases that one lucky seed hides.
