"""Command-line program of the A-Maze-ing project.

Reads a KEY=VALUE configuration file, asks :mod:`mazegen` for a maze, writes
the output file and shows the maze in the terminal with a small menu. All
foreseeable problems end as one "Error: ..." line and the exit code 1.

Usage:
    python3 a_maze_ing.py config.txt
"""
from dataclasses import dataclass
import sys
from mazegen import MazeGenerator


class ConfigError(ValueError):
    """Configuration cannot describe a valid maze."""


# ANSI colours offered by the menu: no colour, then four wall colours.
WALL_COLORS = ("", "\033[36m", "\033[32m", "\033[35m", "\033[33m")
MOTIF_COLOR = "\033[31m"


@dataclass
class Settings:
    """Validated configuration of one maze.

    Attributes:
        width: Number of columns.
        height: Number of rows.
        entry: Entry cell (x, y).
        exit: Exit cell (x, y).
        output_file: Where the maze is written.
        perfect: True for a single path, False for a playable board.
        seed: Seed for reproducible mazes, or None.
    """

    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None = None


def coordinate(value: str) -> tuple[int, int]:
    """Parse an "x,y" pair.

    Args:
        value: The text to read, for example "19,14".

    Returns:
        The pair as (x, y).

    Raises:
        ValueError: If the text is not exactly two integers.
    """
    x, y = value.split(",")
    return int(x), int(y)


def load(path: str) -> Settings:
    """Read a configuration file and check that it describes a valid maze.

    Comments (#) and blank lines are ignored, every mandatory key must be
    present, and the values are converted and checked before use.

    Args:
        path: Path of the configuration file.

    Returns:
        The validated settings.

    Raises:
        ConfigError: If a line, a key or a value is invalid.
        OSError: If the file cannot be read.
    """
    values: dict[str, str] = {}
    with open(path) as source:
        for number, line in enumerate(source, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if "=" not in line:
                raise ConfigError(f"line {number}: expected KEY=VALUE")
            key, value = (part.strip() for part in line.split("=", 1))
            if not key or key in values:
                raise ConfigError(f"line {number}: empty or repeated key")
            values[key] = value
    for key in ("WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"):
        if key not in values:
            raise ConfigError(f"missing {key}")
    try:
        width, height = int(values["WIDTH"]), int(values["HEIGHT"])
        entry, exit_pos = coordinate(
            values["ENTRY"]), coordinate(
            values["EXIT"])
        seed = int(values["SEED"]) if "SEED" in values else None
    except ValueError as error:
        raise ConfigError(f"invalid number or coordinate: {error}") from error
    if width < 2 or height < 2:
        raise ConfigError("WIDTH and HEIGHT must each be at least 2")
    for x, y in (entry, exit_pos):
        if not (0 <= x < width and 0 <= y < height):
            raise ConfigError("ENTRY and EXIT must be inside the maze")
    if entry == exit_pos:
        raise ConfigError("ENTRY and EXIT must differ")
    if values["PERFECT"].lower() not in ("true", "false"):
        raise ConfigError("PERFECT must be True or False")
    if not values["OUTPUT_FILE"]:
        raise ConfigError("OUTPUT_FILE must not be empty")
    return Settings(width, height, entry, exit_pos, values["OUTPUT_FILE"],
                    values["PERFECT"].lower() == "true", seed)


def menu(maze: MazeGenerator, settings: Settings) -> None:
    """Show the maze and handle the user interactions.

    Options: regenerate a new maze (and rewrite the output file), show or
    hide the shortest path, change the wall colours, colour the "42", quit.

    Args:
        maze: The generator holding the maze to display.
        settings: The settings, used to rewrite the output file.

    Raises:
        OSError: If the output file cannot be rewritten.
    """
    show_path, color_index, motif_color = False, 0, ""
    while True:
        print(maze.motif_message)
        print(maze.render(show_path, WALL_COLORS[color_index], motif_color))
        choice = input("1 regenerate | 2 path | 3 colour | 4 motif colour"
                       " | 5 quit: ").strip()
        if choice == "1":
            maze.generate()
            maze.write(settings.output_file)
        elif choice == "2":
            show_path = not show_path
        elif choice == "3":
            color_index = (color_index + 1) % len(WALL_COLORS)
        elif choice == "4":
            motif_color = "" if motif_color else MOTIF_COLOR
        elif choice == "5":
            return


def main() -> None:
    """Run the program and report every problem without a traceback.

    Exits with the status 1 after an error, and 0 after a normal quit, so
    that scripts and the Moulinette can tell the difference.
    """
    try:
        if len(sys.argv) != 2:
            raise ConfigError("usage: python3 a_maze_ing.py config.txt")
        settings = load(sys.argv[1])
        maze = MazeGenerator(settings.width, settings.height, settings.entry,
                             settings.exit, settings.perfect, settings.seed)
        maze.generate()
        maze.write(settings.output_file)
        menu(maze, settings)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
    except (ValueError, OSError) as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
