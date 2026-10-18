
"""Terminal display and interactive controls for A-Maze-ing."""

import shutil

from mazegen import DIRECTIONS, MazeGenerator


class MazeDisplay:
    """Render and control a generated maze in the terminal."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    COLORS = {
        "Cyan": "\033[36m",
        "Green": "\033[32m",
        "Yellow": "\033[33m",
        "Magenta": "\033[35m",
        "Blue": "\033[34m",
        "White": "\033[37m",
    }

    def __init__(
        self,
        maze: MazeGenerator,
        output_file: str,
    ) -> None:
        """Initialize the display."""
        self.maze = maze
        self.output_file = output_file
        self.show_path = True
        self.color_index = 0

    @property
    def wall_color(self) -> str:
        """Return the selected wall colour."""
        return list(self.COLORS.values())[self.color_index]

    @property
    def color_name(self) -> str:
        """Return the selected colour name."""
        return list(self.COLORS)[self.color_index]

    def _paint(self, text: str, color: str) -> str:
        """Apply an ANSI colour to text."""
        if not color:
            return text
        return f"{color}{text}{self.RESET}"

    def _path_cells(self) -> set[tuple[int, int]]:
        """Return the cells belonging to the shortest path."""
        cells = {self.maze.entry}
        x, y = self.maze.entry

        for letter in self.maze.solve():
            direction = next(
                item for item in DIRECTIONS if item[4] == letter
            )
            x += direction[2]
            y += direction[3]
            cells.add((x, y))

        return cells

    def render(self) -> str:
        """Render the maze with aligned two-character cell interiors."""
        width = self.maze.width
        height = self.maze.height
        grid = self.maze.grid
        path = self._path_cells() if self.show_path else set()
        walls = self.wall_color
        rows: list[str] = []

        def horizontal(x: int, y: int, bit: int) -> str:
            """Render a horizontal cell boundary."""
            if grid[y][x] & bit:
                return self._paint("──", walls)
            return "  "

        def vertical(x: int, y: int, bit: int) -> str:
            """Render a vertical cell boundary."""
            if grid[y][x] & bit:
                return self._paint("│", walls)
            return " "

        # Top border.
        top = self._paint("┌", walls)
        for x in range(width):
            top += horizontal(x, 0, 1)
            top += self._paint(
                "┬" if x < width - 1 else "┐",
                walls,
            )
        rows.append(top)

        for y in range(height):
            # Cell contents.
            middle = ""
            for x in range(width):
                middle += vertical(x, y, 8)
                cell = (x, y)

                if cell == self.maze.entry:
                    mark = self._paint("S ", "\033[32m")
                elif cell == self.maze.exit:
                    mark = self._paint("E ", "\033[31m")
                elif cell in self.maze.blocked:
                    mark = self._paint("42", "\033[33m")
                elif self.show_path and cell in path:
                    mark = self._paint("· ", "\033[32m")
                else:
                    mark = "  "

                middle += mark

            middle += self._paint("│", walls)
            rows.append(middle)

            # Boundary below this row.
            is_bottom = y == height - 1
            boundary = self._paint(
                "└" if is_bottom else "├",
                walls,
            )

            for x in range(width):
                boundary += horizontal(x, y, 4)

                if is_bottom:
                    junction = "┴" if x < width - 1 else "┘"
                else:
                    junction = "┼" if x < width - 1 else "┤"

                boundary += self._paint(junction, walls)

            rows.append(boundary)

        return "\n".join(rows)

    def _clear_screen(self) -> None:
        """Clear the terminal display."""
        print("\033[2J\033[H", end="")

    def _header(self) -> None:
        """Display the title and maze status."""
        terminal_width = shutil.get_terminal_size((80, 24)).columns
        width = min(max(self.maze.width * 4 + 1, 40), terminal_width)
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
        print(
            f" MODE: {'PERFECT' if self.maze.perfect else 'PLAYABLE'}"
            f"   PATH: {'ON' if self.show_path else 'OFF'}"
        )
        print(f" ENTRY: {self.maze.entry}   EXIT: {self.maze.exit}")
        print(f" WALLS: {self.color_name}")

        if self.maze.motif_message:
            print(
                self._paint(
                    " NOTE: 42 motif unavailable for this maze size.",
                    "\033[33m",
                )
            )

        print()

    def _menu(self) -> None:
        """Display keyboard controls."""
        print(self._paint(" CONTROLS", self.BOLD))
        print(" [R]  Regenerate maze")
        print(" [P]  Show / hide shortest path")
        print(" [C]  Change wall colour")
        print(" [Q]  Quit")
        print()

    def _regenerate(self) -> None:
        """Generate a new maze and save it."""
        self.maze.generate()
        self.maze.write(self.output_file)

    def run(self) -> None:
        """Run the interactive terminal interface."""
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
                    print(f"Could not regenerate maze: {error}")
                    input("Press Enter to continue...")
            elif choice == "p":
                self.show_path = not self.show_path
            elif choice == "c":
                self.color_index = (
                    self.color_index + 1
                ) % len(self.COLORS)
            elif choice == "q":
                print("Goodbye.")
                break
            else:
                print("Invalid option. Choose R, P, C, or Q.")
                input("Press Enter to continue...")
