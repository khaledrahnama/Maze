
"""Terminal display and interactive controls for A-Maze-ing.

This module is the user interface of the command-line program: it draws a
maze built by :mod:`mazegen` with box-drawing characters and runs the menu.
It is deliberately kept out of the reusable module, which must stay free of
input and output.

The picture is built on a character canvas of (height * 2 + 1) rows and
(width * CELL_WIDTH + 1) columns: even rows carry horizontal walls, odd rows
carry cells and vertical walls. Walls are drawn first, then the solution
path, then the marks for the entry, the exit and the "42".
"""

import shutil

from mazegen import DIRECTIONS, MazeGenerator


class MazeDisplay:
    """Render and control a generated maze in the terminal.

    Attributes:
        maze: The generator holding the maze to show.
        output_file: File rewritten when the user regenerates the maze.
        show_path: Whether the shortest path is currently drawn.
        color_index: Index of the current wall colour in :attr:`COLORS`.
        motif_index: Index of the current "42" colour in :attr:`MOTIF_COLORS`.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[1;32m"
    RED = "\033[1;31m"
    YELLOW = "\033[1;33m"

    COLORS = {
        "Cyan": "\033[36m",
        "Green": "\033[32m",
        "Yellow": "\033[33m",
        "Magenta": "\033[35m",
        "Blue": "\033[34m",
        "White": "\033[37m",
    }

    # Direction letters use the same convention as mazegen.py.
    OPPOSITE = {
        "N": "S",
        "E": "W",
        "S": "N",
        "W": "E",
    }

    # Colours offered for the "42" motif by the [M] control.
    MOTIF_COLORS = {
        "Yellow": "\033[1;33m",
        "Red": "\033[1;31m",
        "Magenta": "\033[1;35m",
        "Blue": "\033[1;34m",
    }

    PATH_CHARS = {
        frozenset(("N", "S")): "┃",
        frozenset(("E", "W")): "━",
        frozenset(("N", "E")): "┗",
        frozenset(("N", "W")): "┛",
        frozenset(("S", "E")): "┏",
        frozenset(("S", "W")): "┓",
        frozenset(("N", "E", "S")): "┣",
        frozenset(("N", "W", "S")): "┫",
        frozenset(("E", "S", "W")): "┳",
        frozenset(("N", "E", "W")): "┻",
        frozenset(("N", "E", "S", "W")): "╋",
    }

    # Wall bitmasks: N=1, E=2, S=4, W=8.
    NORTH = 1
    EAST = 2
    SOUTH = 4
    WEST = 8

    CELL_WIDTH = 4

    def __init__(
        self,
        maze: MazeGenerator,
        output_file: str,
    ) -> None:
        """Prepare the display for one maze.

        Args:
            maze: A generator whose :meth:`mazegen.MazeGenerator.generate`
                has already been called.
            output_file: Path rewritten when the user regenerates the maze.
        """
        self.maze = maze
        self.output_file = output_file
        self.show_path = True
        self.color_index = 0
        self.motif_index = 0

    @property
    def wall_color(self) -> str:
        """str: ANSI escape code of the current wall colour."""
        return list(self.COLORS.values())[self.color_index]

    @property
    def color_name(self) -> str:
        """str: Readable name of the current wall colour."""
        return list(self.COLORS)[self.color_index]

    @property
    def motif_color(self) -> str:
        """str: ANSI escape code of the current "42" colour."""
        return list(self.MOTIF_COLORS.values())[self.motif_index]

    @property
    def motif_color_name(self) -> str:
        """str: Readable name of the current "42" colour."""
        return list(self.MOTIF_COLORS)[self.motif_index]

    def _paint(self, text: str, color: str) -> str:
        """Wrap text in an ANSI colour.

        Args:
            text: The text to colour.
            color: An ANSI escape code, or "" to leave the text as it is.

        Returns:
            The text, followed by a reset code when a colour was applied.
        """
        if not color:
            return text
        return f"{color}{text}{self.RESET}"

    def _path_directions(
        self,
    ) -> dict[tuple[int, int], set[str]]:
        """Walk the solution and note how it enters and leaves each cell.

        Returns:
            For every cell on the shortest path, the set of directions used
            there, which decides the corner glyph drawn in that cell.

        Raises:
            ValueError: If the maze has no solution.
        """
        connections: dict[tuple[int, int], set[str]] = {}
        x, y = self.maze.entry
        connections[(x, y)] = set()

        for letter in self.maze.solve():
            direction = next(
                item for item in DIRECTIONS if item[4] == letter
            )
            dx, dy = direction[2], direction[3]
            nx, ny = x + dx, y + dy

            connections.setdefault((x, y), set()).add(letter)
            connections.setdefault((nx, ny), set()).add(
                self.OPPOSITE[letter]
            )
            x, y = nx, ny

        return connections

    def _wall_bits(self, x: int, y: int) -> int:
        """Return the wall bits of a cell, with the border forced closed.

        Args:
            x: Column of the cell.
            y: Row of the cell.

        Returns:
            The cell value with the outer border bits set, so the frame is
            always drawn even if a generator opened a border wall.
        """
        bits = self.maze.grid[y][x]

        if y == 0:
            bits |= self.NORTH
        if x == self.maze.width - 1:
            bits |= self.EAST
        if y == self.maze.height - 1:
            bits |= self.SOUTH
        if x == 0:
            bits |= self.WEST

        return bits

    def _junction(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> str:
        """Pick the box-drawing character for one wall intersection.

        Args:
            x: Column of the intersection, from 0 to width.
            y: Row of the intersection, from 0 to height.
            width: Number of columns of the maze.
            height: Number of rows of the maze.

        Returns:
            The corner, edge or cross character for that position.
        """
        if x == 0 and y == 0:
            return "┏"
        if x == width and y == 0:
            return "┓"
        if x == 0 and y == height:
            return "┗"
        if x == width and y == height:
            return "┛"
        if y == 0:
            return "┳"
        if y == height:
            return "┻"
        if x == 0:
            return "┣"
        if x == width:
            return "┫"
        return "╋"

    def _draw_walls(
        self,
        canvas: list[list[str]],
        width: int,
        height: int,
    ) -> None:
        """Draw every wall of the maze on the canvas.

        Args:
            canvas: The character grid to draw on, changed in place.
            width: Number of columns of the maze.
            height: Number of rows of the maze.
        """
        cell_width = self.CELL_WIDTH

        for y in range(height):
            for x in range(width):
                bits = self._wall_bits(x, y)
                left = x * cell_width
                right = (x + 1) * cell_width
                top = 2 * y
                bottom = 2 * y + 2

                if bits & self.NORTH:
                    for col in range(left + 1, right):
                        canvas[top][col] = "━"

                if bits & self.SOUTH:
                    for col in range(left + 1, right):
                        canvas[bottom][col] = "━"

                if bits & self.WEST:
                    canvas[top + 1][left] = "┃"

                if bits & self.EAST:
                    canvas[top + 1][right] = "┃"

        # Junctions are drawn after wall segments.
        for y in range(height + 1):
            for x in range(width + 1):
                canvas[2 * y][x * cell_width] = self._junction(
                    x, y, width, height
                )

    def _draw_path(
        self,
        canvas: list[list[str]],
        path: dict[tuple[int, int], set[str]],
    ) -> None:
        """Draw the solution path, never crossing a closed wall.

        Args:
            canvas: The character grid to draw on, changed in place.
            path: The directions used in each cell of the path.
        """
        cell_width = self.CELL_WIDTH

        for (x, y), directions in path.items():
            center_x = x * cell_width + cell_width // 2
            center_y = 2 * y + 1

            # Draw horizontal connections inside the cell.
            if "W" in directions:
                if not (self._wall_bits(x, y) & self.WEST):
                    canvas[center_y][center_x - 1] = "━"

            if "E" in directions:
                if not (self._wall_bits(x, y) & self.EAST):
                    canvas[center_y][center_x + 1] = "━"

            # Draw vertical connections inside the cell.
            if "N" in directions:
                if not (self._wall_bits(x, y) & self.NORTH):
                    canvas[center_y - 1][center_x] = "┃"

            if "S" in directions:
                if not (self._wall_bits(x, y) & self.SOUTH):
                    canvas[center_y + 1][center_x] = "┃"

            # Draw connections across open cell boundaries.
            if "E" in directions and x + 1 < self.maze.width:
                if not (self._wall_bits(x, y) & self.EAST):
                    canvas[center_y][center_x + 2] = "━"

            if "S" in directions and y + 1 < self.maze.height:
                if not (self._wall_bits(x, y) & self.SOUTH):
                    canvas[center_y + 1][center_x] = "┃"

    def _draw_cell_marks(
        self,
        canvas: list[list[str]],
        colors: list[list[str]],
        path: dict[tuple[int, int], set[str]],
    ) -> None:
        """Mark the entry, the exit, the "42" and the path cells.

        Args:
            canvas: The character grid to draw on, changed in place.
            colors: The colour of each character, changed in place.
            path: The directions used in each cell of the path.
        """
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                cell = (x, y)
                row = 2 * y + 1
                col = x * self.CELL_WIDTH + self.CELL_WIDTH // 2

                if cell == self.maze.entry:
                    canvas[row][col] = "S"
                    colors[row][col] = self.GREEN
                elif cell == self.maze.exit:
                    canvas[row][col] = "E"
                    colors[row][col] = self.RED
                elif cell in self.maze.blocked:
                    canvas[row][col - 1] = "█"
                    canvas[row][col] = "█"
                    colors[row][col - 1] = self.motif_color
                    colors[row][col] = self.motif_color
                elif self.show_path and cell in path:
                    directions = frozenset(path[cell])
                    char = self.PATH_CHARS.get(directions)

                    if char:
                        canvas[row][col] = char
                        colors[row][col] = self.GREEN
                    elif directions:
                        # Start/end cells may have only one connection.
                        direction = next(iter(directions))
                        canvas[row][col] = (
                            "━" if direction in ("E", "W") else "┃"
                        )
                        colors[row][col] = self.GREEN

    def render(self) -> str:
        """Build the whole picture.

        Returns:
            The maze as one multi-line coloured string: "S" is the entry,
            "E" the exit, blocks are the "42" and the line is the solution.

        Raises:
            ValueError: If the maze has no solution.
        """
        width = self.maze.width
        height = self.maze.height
        canvas_width = width * self.CELL_WIDTH + 1
        canvas_height = height * 2 + 1

        canvas = [
            [" " for _ in range(canvas_width)]
            for _ in range(canvas_height)
        ]
        colors = [
            ["" for _ in range(canvas_width)]
            for _ in range(canvas_height)
        ]

        path = self._path_directions() if self.show_path else {}

        self._draw_walls(canvas, width, height)

        if self.show_path:
            self._draw_path(canvas, path)

        self._draw_cell_marks(canvas, colors, path)

        rows: list[str] = []

        for row_index, row in enumerate(canvas):
            rendered = ""

            for col_index, char in enumerate(row):
                if char in (" ",):
                    rendered += char
                    continue

                # Keep outer walls and junctions in the wall colour.
                is_junction = (
                    row_index % 2 == 0
                    and col_index % self.CELL_WIDTH == 0
                )
                is_outer_wall = (
                    row_index == 0
                    or row_index == canvas_height - 1
                    or col_index == 0
                    or col_index == canvas_width - 1
                )

                color = self.wall_color if (
                    is_junction or is_outer_wall
                ) else colors[row_index][col_index]

                if not color:
                    color = self.wall_color

                rendered += self._paint(char, color)

            rows.append(rendered)

        return "\n".join(rows)

    def _clear_screen(self) -> None:
        """Move the cursor home and clear the terminal."""
        print("\033[2J\033[H", end="")

    def _header(self) -> None:
        """Print the title and the current state of the maze."""
        terminal_width = shutil.get_terminal_size((80, 24)).columns
        width = min(
            max(self.maze.width * self.CELL_WIDTH + 1, 40),
            terminal_width,
        )
        line = "═" * width

        print(self._paint(line, self.wall_color))
        print(self._paint("A - M A Z E - I N G".center(width), self.BOLD))
        print(
            self._paint(
                "42 SCHOOL | MAZE GENERATOR".center(width),
                self.DIM,
            )
        )
        print(self._paint(line, self.wall_color))

        mode = "PERFECT" if self.maze.perfect else "PLAYABLE"
        path_status = "ON" if self.show_path else "OFF"

        print(f" MODE: {mode}   PATH: {path_status}")
        print(f" ENTRY: {self.maze.entry}   EXIT: {self.maze.exit}")
        print(f" WALLS: {self.color_name}   42: {self.motif_color_name}")

        if self.maze.motif_message:
            print(
                self._paint(
                    f" NOTE: {self.maze.motif_message}",
                    self.YELLOW,
                )
            )

        print()

    def _menu(self) -> None:
        """Print the keyboard controls."""
        print(self._paint(" CONTROLS", self.BOLD))
        print(" [R]  Regenerate maze")
        print(" [P]  Show / hide shortest path")
        print(" [C]  Change wall colour")
        print(" [M]  Change 42 colour")
        print(" [Q]  Quit")
        print()

    def _regenerate(self) -> None:
        """Build a new maze and rewrite the output file.

        Raises:
            ValueError: If a playable board cannot be braided at this size.
            OSError: If the output file cannot be written.
        """
        self.maze.generate()
        self.maze.write(self.output_file)

    def _pause(self, message: str) -> None:
        """Show a message and wait for Enter, ignoring the end of input.

        Args:
            message: The line to show before waiting.
        """
        print(message)
        try:
            input(" Press Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass

    def run(self) -> None:
        """Show the maze and handle the controls until the user quits."""
        while True:
            self._clear_screen()
            self._header()
            print(self.render())
            self._menu()

            try:
                choice = input(" Choose an option: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if choice == "r":
                try:
                    self._regenerate()
                except (ValueError, OSError) as error:
                    self._pause(f" Could not regenerate maze: {error}")
            elif choice == "p":
                self.show_path = not self.show_path
            elif choice == "c":
                self.color_index = (
                    self.color_index + 1
                ) % len(self.COLORS)
            elif choice == "m":
                self.motif_index = (
                    self.motif_index + 1
                ) % len(self.MOTIF_COLORS)
            elif choice == "q":
                print("Goodbye.")
                break
            else:
                self._pause(" Invalid option. Choose R, P, C, M or Q.")
