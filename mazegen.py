"""Seeded maze generation, shortest paths and terminal rendering.

This module is the reusable part of the A-Maze-ing project. It contains a
single class, :class:`MazeGenerator`, and depends only on the standard
library, so another project can install it with pip and import it.

Quick start:
    >>> from mazegen import MazeGenerator
    >>> maze = MazeGenerator(10, 6, (0, 0), (9, 5), perfect=True, seed=42)
    >>> grid = maze.generate()      # the structure: one int per cell
    >>> path = maze.solve()         # a solution: "SSEEN..." (N/E/S/W)
    >>> print(maze.render())        # an ASCII picture of the maze

Custom parameters:
    width, height   size in cells (at least 2 by 2)
    entry, exit     (x, y) cells, different and inside the maze
    perfect         True: exactly one path between any two cells.
                    False: a Pac-Man-like board with loops and no dead ends.
    seed            any integer: the same seed rebuilds the same maze.

Accessing the generated structure:
    maze.grid       list of rows; each cell is an int whose bits say which
                    walls are closed: 1 north, 2 east, 4 south, 8 west
                    (so 15 means fully closed, 0 means fully open).
    maze.blocked    the cells of the closed "42" motif.
    maze.solve()    the shortest entry-to-exit path as N/E/S/W letters.
    maze.write(f)   the same data in the subject's output-file format.

The structure kept in memory (integers with wall bits) is the same encoding
as the output file, so a reader of either format sees identical walls.
"""
from collections import deque
import random

__all__ = ["MazeGenerator", "DIRECTIONS"]
__version__ = "1.0.0"

# North, east, south, west: bit, opposite bit, coordinate delta, path letter.
DIRECTIONS = [(1, 4, 0, -1, "N"), (2, 8, 1, 0, "E"),
              (4, 1, 0, 1, "S"), (8, 2, -1, 0, "W")]


class MazeGenerator:
    """Create connected mazes with reciprocal walls and a closed 42 motif.

    Attributes:
        width: Number of columns.
        height: Number of rows.
        entry: Entry cell as (x, y).
        exit: Exit cell as (x, y).
        perfect: True for a single path, False for a braided board.
        random: Private random generator, seeded for reproducibility.
        grid: Rows of wall masks; empty until :meth:`generate` is called.
        blocked: Cells of the "42" motif, kept fully closed.
        motif_message: Whether the motif was drawn, or why it was skipped.

    Example:
        >>> maze = MazeGenerator(12, 9, (0, 0), (11, 8), seed=1)
        >>> _ = maze.generate()
        >>> maze.grid[0][0] & 1        # north wall of the first cell
        1
    """

    def __init__(self, width: int, height: int, entry: tuple[int, int],
                 exit: tuple[int, int], perfect: bool = True,
                 seed: int | None = None) -> None:
        """Validate the parameters and prepare a seeded generator.

        Args:
            width: Number of columns, at least 2.
            height: Number of rows, at least 2.
            entry: Entry cell (x, y), inside the maze.
            exit: Exit cell (x, y), inside the maze and not the entry.
            perfect: True for one single path, False for a playable board.
            seed: Seed for reproducible mazes; None picks a random one.

        Raises:
            ValueError: If the size is too small, the cells are outside the
                maze, or the entry and the exit are the same cell.
        """
        if width < 2 or height < 2:
            raise ValueError("maze dimensions must be at least 2")
        if entry == exit:
            raise ValueError("entry and exit must differ")
        if any(not (0 <= x < width and 0 <= y < height)
               for x, y in (entry, exit)):
            raise ValueError("entry and exit must lie inside the maze")
        self.width, self.height = width, height
        self.entry, self.exit = entry, exit
        self.perfect = perfect
        self.random = random.Random(seed)
        self.grid: list[list[int]] = []
        self.blocked: set[tuple[int, int]] = set()
        self.motif_message = ""

    def neighbors(self, cell: tuple[int, int]
                  ) -> list[tuple[int, int, int, int, str]]:
        """Return the usable neighbours of a cell.

        Args:
            cell: The cell (x, y) to look around.

        Returns:
            One tuple per neighbour inside the maze and outside the motif:
            (x, y, wall bit of this cell, wall bit of the neighbour, letter).
        """
        x, y = cell
        return [(x + dx, y + dy, bit, opposite, letter)
                for bit, opposite, dx, dy, letter in DIRECTIONS
                if 0 <= x + dx < self.width and 0 <= y + dy < self.height
                and (x + dx, y + dy) not in self.blocked]

    def _place_42(self) -> None:
        """Place a centred 42 motif while preserving connectivity."""
        pattern = [
            "#..#.####",
            "#..#....#",
            "####.####",
            "...#.#...",
            "...#.####",
        ]
        ph = len(pattern)
        pw = len(pattern[0])

        protected = {
            self.entry,
            self.exit,
            (0, 0),
            (self.width - 1, 0),
            (0, self.height - 1),
            (self.width - 1, self.height - 1),
            (self.width // 2, self.height // 2),
        }

        self.blocked = set()

        if self.width < pw or self.height < ph:
            self.motif_message = "42 omitted: maze too small."
            return

        center_x = (self.width - pw) // 2
        center_y = (self.height - ph) // 2

        # Try the centre first, then progressively nearby positions.
        positions = [
            (center_x + dx, center_y + dy)
            for distance in range(max(self.width, self.height))
            for dy in range(-distance, distance + 1)
            for dx in range(-distance, distance + 1)
            if max(abs(dx), abs(dy)) == distance
        ]

        for ox, oy in positions:
            if ox < 0 or oy < 0:
                continue
            if ox + pw > self.width or oy + ph > self.height:
                continue

            cells = {
                (ox + x, oy + y)
                for y, row in enumerate(pattern)
                for x, value in enumerate(row)
                if value == "#"
            }

            if cells & protected:
                continue

            self.blocked = cells
            seen = {self.entry}
            stack = [self.entry]

            while stack:
                current = stack.pop()
                for x, y, *_ in self.neighbors(current):
                    if (x, y) not in seen:
                        seen.add((x, y))
                        stack.append((x, y))

            if len(seen) == self.width * self.height - len(cells):
                self.motif_message = "42 motif included."
                return

        self.blocked = set()
        self.motif_message = "42 omitted: no valid placement found."

    def _open(self, cell: tuple[int, int],
              neighbor: tuple[int, int, int, int, str]) -> None:
        """Remove a shared wall from both adjacent cells.

        Clearing the bit on both sides in one place is what keeps the data
        coherent: no other code writes wall bits.

        Args:
            cell: The cell (x, y) whose wall is opened.
            neighbor: A tuple from :meth:`neighbors` describing the other side.
        """
        x, y = cell
        nx, ny, bit, opposite, _ = neighbor
        self.grid[y][x] &= ~bit
        self.grid[ny][nx] &= ~opposite

    def _open_square(self) -> bool:
        """Tell whether a forbidden open area exists.

        Returns:
            True if some 3 by 3 block of cells has every inner wall open,
            which the subject forbids (2 by 3 is still allowed).
        """
        for y in range(self.height - 2):
            for x in range(self.width - 2):
                horizontal = all(not self.grid[yy][xx] & 2
                                 for yy in range(y, y + 3)
                                 for xx in range(x, x + 2))
                vertical = all(not self.grid[yy][xx] & 4
                               for yy in range(y, y + 2)
                               for xx in range(x, x + 3))
                if horizontal and vertical:
                    return True
        return False

    def _braid(self) -> None:
        """Turn the perfect maze into a playable board.

        Opens one more wall at each dead end, then keeps opening walls until
        the board has at least two independent loops, undoing any change that
        would create a 3 by 3 open area.

        Raises:
            ValueError: If the maze is too small to reach two loops with at
                most a couple of dead ends.
        """
        cells = [(x, y) for y in range(self.height) for x in range(self.width)
                 if (x, y) not in self.blocked]
        self.random.shuffle(cells)
        for cell in cells:
            x, y = cell
            if self.grid[y][x].bit_count() != 3:
                continue
            options = self.neighbors(cell)
            self.random.shuffle(options)
            for neighbor in options:
                nx, ny, bit, opposite, _ = neighbor
                if not self.grid[y][x] & bit:
                    continue
                self._open(cell, neighbor)
                if not self._open_square():
                    break
                self.grid[y][x] |= bit
                self.grid[ny][nx] |= opposite
        # Ensure at least two independent cycles when the size permits it.
        vertices = len(cells)
        edges = sum(4 - self.grid[y][x].bit_count() for x, y in cells) // 2
        for cell in cells:
            if edges - vertices + 1 >= 2:
                break
            x, y = cell
            for neighbor in self.neighbors(cell):
                nx, ny, bit, opposite, _ = neighbor
                if self.grid[y][x] & bit:
                    self._open(cell, neighbor)
                    if self._open_square():
                        self.grid[y][x] |= bit
                        self.grid[ny][nx] |= opposite
                    else:
                        edges += 1
                        break
        dead_ends = sum(self.grid[y][x].bit_count() == 3 for x, y in cells)
        if edges - vertices + 1 < 2 or dead_ends > 2:
            raise ValueError(
                "cannot braid this layout; try a larger maze or another seed")

    def generate(self) -> list[list[int]]:
        """Build a new maze and return its structure.

        Places the motif, carves a spanning tree (see :meth:`_carve`) and,
        when ``perfect`` is False, braids the result into a playable board.
        If the motif leaves too little room to braid, it is dropped and the
        maze is carved again, as the subject allows for small mazes.

        Returns:
            The grid: one list per row, one integer of wall bits per cell.

        Raises:
            ValueError: If even without the motif no playable board fits.
        """
        self._place_42()
        self._carve()
        if not self.perfect:
            try:
                self._braid()
            except ValueError:
                if not self.blocked:
                    raise
                # The motif leaves too little room for a playable board at
                # this size: the subject allows dropping it, with a message.
                self.blocked = set()
                self.motif_message = (
                    "42 omitted: no room left for a playable board.")
                self._carve()
                self._braid()
        return self.grid

    def _carve(self) -> None:
        """Carve a spanning tree with a randomised depth-first search.

        Starts from the entry and uses an explicit stack, so even large
        mazes cannot reach Python's recursion limit. Cells of the motif are
        never entered, so their four walls stay closed.
        """
        self.grid = [[15] * self.width for _ in range(self.height)]
        visited, stack = {self.entry}, [self.entry]
        while stack:
            cell = stack[-1]
            choices = [
                n for n in self.neighbors(cell) if (
                    n[0], n[1]) not in visited]
            if not choices:
                stack.pop()
                continue
            chosen = self.random.choice(choices)
            self._open(cell, chosen)
            next_cell = (chosen[0], chosen[1])
            visited.add(next_cell)
            stack.append(next_cell)

    def solve(self) -> str:
        """Find the shortest way out.

        Uses breadth-first search, which visits cells in order of distance,
        so the first route found to the exit is a shortest one.

        Returns:
            The path from the entry to the exit as N/E/S/W letters, or an
            empty string when the entry is the exit.

        Raises:
            ValueError: If :meth:`generate` has not been called yet, or the
                exit cannot be reached.
        """
        if not self.grid:
            raise ValueError("call generate() before solve()")
        queue = deque([self.entry])
        previous: dict[tuple[int, int], tuple[tuple[int, int], str]] = {}
        seen = {self.entry}
        while queue:
            cell = queue.popleft()
            if cell == self.exit:
                break
            x, y = cell
            for nx, ny, bit, _, letter in self.neighbors(cell):
                if not self.grid[y][x] & bit and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    previous[(nx, ny)] = (cell, letter)
                    queue.append((nx, ny))
        if self.exit not in seen:
            raise ValueError("the exit cannot be reached from the entry")
        path, cell = [], self.exit
        while cell != self.entry:
            cell, letter = previous[cell]
            path.append(letter)
        return "".join(reversed(path))

    def write(self, filename: str) -> None:
        """Write the maze in the subject's output format.

        One hexadecimal digit per cell, one row per line, then an empty line,
        the entry, the exit and the shortest path. Every line ends with "\n",
        and the context manager closes the file even if writing fails.

        Args:
            filename: Path of the file to create or replace.

        Raises:
            OSError: If the file cannot be written.
            ValueError: If the maze has no solution (see :meth:`solve`).
        """
        with open(filename, "w") as output:
            for row in self.grid:
                output.write("".join(format(value, "X")
                             for value in row) + "\n")
            output.write(f"\n{self.entry[0]},{self.entry[1]}\n")
            output.write(f"{self.exit[0]},{self.exit[1]}\n{self.solve()}\n")

    def render(self, show_path: bool = False, color: str = "",
               motif_color: str = "") -> str:
        """Draw the maze with text.

        Args:
            show_path: Also mark the cells of the shortest path with dots.
            color: ANSI escape code for the walls, for example "\033[36m".
            motif_color: ANSI escape code for the "42" cells.

        Returns:
            The picture as one multi-line string: "E" is the entry, "X" the
            exit, "#" the motif and "." the solution path.
        """
        path = {self.entry}
        x, y = self.entry
        for letter in self.solve():
            _, _, dx, dy, _ = next(d for d in DIRECTIONS if d[4] == letter)
            x, y = x + dx, y + dy
            path.add((x, y))
        rows = []
        for y in range(self.height):
            rows.append("".join("+" + ("---" if self.grid[y][x] & 1 else "   ")
                                for x in range(self.width)) + "+")
            line = ""
            for x in range(self.width):
                cell = (x, y)
                mark = ("E" if cell == self.entry else "X" if cell == self.exit
                        else "#" if cell in self.blocked
                        else "." if show_path and cell in path else " ")
                if motif_color and cell in self.blocked:
                    mark = f"{motif_color}{mark}{color or chr(27) + '[0m'}"
                line += ("|" if self.grid[y][x] & 8 else " ") + f" {mark} "
            rows.append(line + "|")
        rows.append("+---" * self.width + "+")
        return color + "\n".join(rows) + ("\033[0m" if color else "")
