"""Seeded maze generation, shortest paths and terminal rendering."""
from collections import deque
import random

# North, east, south, west: bit, opposite bit, coordinate delta, path letter.
DIRECTIONS = [(1, 4, 0, -1, "N"), (2, 8, 1, 0, "E"),
              (4, 1, 0, 1, "S"), (8, 2, -1, 0, "W")]


class MazeGenerator:
    """Create connected mazes with reciprocal walls and a closed 42 motif."""

    def __init__(self, width: int, height: int, entry: tuple[int, int],
                 exit: tuple[int, int], perfect: bool = True,
                 seed: int | None = None) -> None:
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
        """Return interior neighbours with wall and direction data."""
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
        """Remove a shared wall from both adjacent cells."""
        x, y = cell
        nx, ny, bit, opposite, _ = neighbor
        self.grid[y][x] &= ~bit
        self.grid[ny][nx] &= ~opposite

    def _open_square(self) -> bool:
        """Detect a fully open 3 by 3 region of cells."""
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
        """Remove dead ends without opening a 3 by 3 room."""
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
        """Carve a spanning tree, then optionally add passages for loops."""
        self.grid = [[15] * self.width for _ in range(self.height)]
        self._place_42()
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
        if not self.perfect:
            self._braid()
        return self.grid

    def solve(self) -> str:
        """Return a shortest path as N/E/S/W directions using BFS."""
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
        path, cell = [], self.exit
        while cell != self.entry:
            cell, letter = previous[cell]
            path.append(letter)
        return "".join(reversed(path))

    def write(self, filename: str) -> None:
        """Write wall masks, endpoints and the shortest solution path."""
        with open(filename, "w") as output:
            for row in self.grid:
                output.write("".join(format(value, "X")
                             for value in row) + "\n")
            output.write(f"\n{self.entry[0]},{self.entry[1]}\n")
            output.write(f"{self.exit[0]},{self.exit[1]}\n{self.solve()}\n")

    def render(self, show_path: bool = False, color: str = "") -> str:
        """Render walls, endpoints and an optional solution with ASCII."""
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
                line += ("|" if self.grid[y][x] & 8 else " ") + f" {mark} "
            rows.append(line + "|")
        rows.append("+---" * self.width + "+")
        return color + "\n".join(rows) + ("\033[0m" if color else "")
