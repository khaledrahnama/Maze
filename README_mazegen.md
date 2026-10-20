# mazegen

A small, reusable maze generator written in pure Python (standard library
only, Python 3.10 or later). It builds seeded, reproducible mazes in two
modes, finds the shortest path, and can write the maze to a file or draw it
as text.

The whole module is one class, `MazeGenerator`, in one file, `mazegen.py`.

## Installation

```sh
pip install mazegen-1.0.0-py3-none-any.whl
# or, from the source distribution:
pip install mazegen-1.0.0.tar.gz
```

To rebuild the package from the sources (in a virtualenv):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install build
.venv/bin/python -m build          # writes dist/mazegen-1.0.0-*.whl and .tar.gz
```

## Basic example

```python
from mazegen import MazeGenerator

maze = MazeGenerator(20, 15, entry=(0, 0), exit=(19, 14), seed=42)
grid = maze.generate()           # build the maze, get its structure
path = maze.solve()              # a shortest solution, e.g. "EESSWS..."

print(maze.render(show_path=True))
print("Solution:", path)
```

Creating the object only stores and checks the parameters; the maze exists
once `generate()` has been called. Calling `generate()` again builds a new,
different maze (the seeded random generator moves on, so the sequence of
mazes is still reproducible).

## Custom parameters

```python
MazeGenerator(width, height, entry, exit, perfect=True, seed=None)
```

| Parameter | Type | Meaning |
| --- | --- | --- |
| `width` | `int` | Number of columns, at least 2. |
| `height` | `int` | Number of rows, at least 2. |
| `entry` | `tuple[int, int]` | Entry cell `(x, y)`; `x` is the column, `y` the row, `(0, 0)` is the top-left cell. |
| `exit` | `tuple[int, int]` | Exit cell `(x, y)`, inside the maze and different from `entry`. |
| `perfect` | `bool` | `True` (default): a perfect maze, exactly one path between any two cells, no loops. `False`: a Pac-Man-like board, fully connected, with open corners and centre, at least two independent loops and no real dead end. |
| `seed` | `int` or `None` | The same seed always rebuilds the same maze. `None` picks a random one. |

Invalid parameters raise `ValueError` straight away:

```python
from mazegen import MazeGenerator

try:
    MazeGenerator(10, 10, entry=(0, 0), exit=(0, 0))
except ValueError as error:
    print(error)                 # entry and exit must differ
```

`generate()` can also raise `ValueError` when no valid board fits, for
example a 2 x 2 maze with `perfect=False`.

Examples:

```python
from mazegen import MazeGenerator

small = MazeGenerator(12, 9, (0, 0), (11, 8), seed=1)                # perfect
board = MazeGenerator(30, 20, (0, 0), (29, 19), perfect=False, seed=7)  # playable
same_a = MazeGenerator(15, 13, (1, 1), (8, 8), seed=23)
same_b = MazeGenerator(15, 13, (1, 1), (8, 8), seed=23)
assert same_a.generate() == same_b.generate()                         # reproducible
```

## Accessing the generated structure

After `generate()`, the maze is available as plain Python data:

| Attribute / method | Content |
| --- | --- |
| `maze.grid` | A list of rows; `maze.grid[y][x]` is an `int` from 0 to 15 whose bits say which walls of that cell are **closed**. `generate()` returns the same list. |
| `maze.blocked` | A `set` of `(x, y)` cells forming the "42" motif; these cells are fully closed (value 15). Empty if the motif did not fit. |
| `maze.motif_message` | Text saying whether the "42" was drawn, or why it was left out. |
| `maze.width`, `maze.height`, `maze.entry`, `maze.exit`, `maze.perfect` | The parameters. |

Wall bits:

| Bit | Value | Wall |
| --- | --- | --- |
| 0 | 1 | North |
| 1 | 2 | East |
| 2 | 4 | South |
| 3 | 8 | West |

So `15` is a fully closed cell, `0` a fully open one, and
`grid[y][x] & 2` is non-zero when the east wall is closed. Neighbouring
cells always agree: if a cell's east wall is open, the west wall of the
cell to its right is open too. The outer border is always closed.

```python
from mazegen import DIRECTIONS, MazeGenerator

maze = MazeGenerator(10, 8, (0, 0), (9, 7), seed=3)
maze.generate()

x, y = 0, 0
walls = maze.grid[y][x]
print("north closed:", bool(walls & 1))
print("east open:   ", not walls & 2)

# DIRECTIONS is the table the module uses internally:
# (wall bit, opposite bit, dx, dy, letter) for N, E, S, W.
for bit, opposite, dx, dy, letter in DIRECTIONS:
    if not walls & bit:
        print(f"from {(x, y)} you can go {letter} to {(x + dx, y + dy)}")
```

## Accessing a solution

`maze.solve()` returns a shortest path from the entry to the exit as a
string of the letters `N`, `E`, `S`, `W` (found with a breadth-first
search). To turn it into the list of visited cells:

```python
from mazegen import DIRECTIONS, MazeGenerator

maze = MazeGenerator(10, 8, (0, 0), (9, 7), seed=3)
maze.generate()

steps = {letter: (dx, dy) for _, _, dx, dy, letter in DIRECTIONS}
x, y = maze.entry
cells = [(x, y)]
for letter in maze.solve():
    dx, dy = steps[letter]
    x, y = x + dx, y + dy
    cells.append((x, y))

assert cells[-1] == maze.exit
print(len(cells) - 1, "steps:", cells)
```

`solve()` raises `ValueError` if `generate()` has not been called yet.

## Output file and text rendering

The in-memory structure is not tied to any file format, but two helpers are
provided:

- `maze.write("maze.txt")` writes the A-Maze-ing output format: one
  hexadecimal digit per cell (the same wall bits), one row per line, then an
  empty line, the entry `x,y`, the exit `x,y` and the shortest path.
- `maze.render(show_path=False, color="", motif_color="")` returns an ASCII
  drawing as a string: `E` is the entry, `X` the exit, `#` the "42" cells and
  `.` the solution path when `show_path=True`. `color` and `motif_color` are
  optional ANSI escape codes, for example `"\033[36m"` for cyan walls.
