"""Command-line program of the A-Maze-ing project.

Reads a KEY=VALUE configuration file, asks :mod:`mazegen` for a maze, writes
the output file and hands it to :mod:`display` for the interactive terminal
view. When ``display.py`` is not available (for example when only the
installed ``mazegen`` package and this file are used), a simpler interactive
view built on :meth:`MazeGenerator.render` is used instead. All foreseeable
problems end as one "Error: ..." line and exit code 1.

Usage:
    python3 a_maze_ing.py config.txt
"""
from dataclasses import dataclass
import sys
from mazegen import MazeGenerator


# Wall colours offered by the simple view (C cycles through them).
SIMPLE_COLORS = [("Cyan", "\033[36m"), ("Green", "\033[32m"),
                 ("Yellow", "\033[33m"), ("Magenta", "\033[35m"),
                 ("White", "\033[37m")]
# Colours of the "42" in the simple view (M cycles through them).
SIMPLE_MOTIF_COLORS = [("Yellow", "\033[1;33m"), ("Red", "\033[1;31m"),
                       ("Green", "\033[1;32m"), ("Blue", "\033[1;34m")]

MAX_SIZE = 500
"""Largest WIDTH or HEIGHT accepted, so a typo cannot freeze the program."""


class ConfigError(ValueError):
    """Configuration cannot describe a valid maze."""


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


def integer(key: str, value: str) -> int:
    """Parse the integer value of a configuration key.

    Args:
        key: Name of the key, used in the error message.
        value: The text to read, for example "20".

    Returns:
        The value as an int.

    Raises:
        ConfigError: If the text is not an integer.
    """
    try:
        return int(value)
    except ValueError:
        raise ConfigError(
            f"{key} must be an integer, got '{value}'") from None


def coordinate(key: str, value: str) -> tuple[int, int]:
    """Parse an "x,y" pair.

    Args:
        key: Name of the key, used in the error message.
        value: The text to read, for example "19,14".

    Returns:
        The pair as (x, y).

    Raises:
        ConfigError: If the text is not exactly two integers.
    """
    parts = value.split(",")
    try:
        if len(parts) != 2:
            raise ValueError
        return int(parts[0]), int(parts[1])
    except ValueError:
        raise ConfigError(
            f"{key} must be two integers 'x,y', got '{value}'") from None


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
            key = key.upper()  # keys are case-insensitive: width=20 is OK
            if not key or key in values:
                raise ConfigError(f"line {number}: empty or repeated key")
            values[key] = value
    for key in ("WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"):
        if key not in values:
            raise ConfigError(f"missing {key}")
    width = integer("WIDTH", values["WIDTH"])
    height = integer("HEIGHT", values["HEIGHT"])
    entry = coordinate("ENTRY", values["ENTRY"])
    exit_pos = coordinate("EXIT", values["EXIT"])
    seed = integer("SEED", values["SEED"]) if "SEED" in values else None
    if width < 2 or height < 2:
        raise ConfigError("WIDTH and HEIGHT must each be at least 2")
    if width > MAX_SIZE or height > MAX_SIZE:
        raise ConfigError(f"WIDTH and HEIGHT must each be at most {MAX_SIZE}")
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


def simple_view(maze: MazeGenerator, output_file: str) -> None:
    """Interactive view that needs nothing but :mod:`mazegen`.

    Used when ``display.py`` is missing. It draws the maze with
    :meth:`MazeGenerator.render` and offers the same mandatory controls:
    regenerate, show/hide the path, change the wall and "42" colours.

    Args:
        maze: A generator on which ``generate()`` has already been called.
        output_file: File rewritten every time the maze is regenerated.
    """
    show_path, wall, motif = True, 0, 0
    while True:
        print("\033[2J\033[H", end="")
        print("A-MAZE-ING (simple view)")
        print(f"PATH: {'ON' if show_path else 'OFF'}   "
              f"WALLS: {SIMPLE_COLORS[wall][0]}   "
              f"42: {SIMPLE_MOTIF_COLORS[motif][0]}")
        if maze.motif_message:
            print(f"NOTE: {maze.motif_message}")
        print(maze.render(show_path, SIMPLE_COLORS[wall][1],
                          SIMPLE_MOTIF_COLORS[motif][1]))
        print("E = entry, X = exit, # = 42, . = shortest path")
        print("[R] regenerate  [P] path  [C] wall colour  [M] 42 colour  "
              "[Q] quit")
        choice = input("Choose an option: ").strip().lower()
        if choice == "r":
            try:
                maze.generate()
                maze.write(output_file)
            except (ValueError, OSError) as error:
                input(f"Could not regenerate maze: {error} (press Enter)")
        elif choice == "p":
            show_path = not show_path
        elif choice == "c":
            wall = (wall + 1) % len(SIMPLE_COLORS)
        elif choice == "m":
            motif = (motif + 1) % len(SIMPLE_MOTIF_COLORS)
        elif choice == "q":
            print("Goodbye.")
            return
        else:
            input("Invalid option. Choose R, P, C, M, or Q (press Enter)")


def show(maze: MazeGenerator, output_file: str) -> None:
    """Open the full display, or the simple view if display.py is missing.

    Args:
        maze: A generator on which ``generate()`` has already been called.
        output_file: File rewritten every time the maze is regenerated.
    """
    try:
        from display import MazeDisplay
    except ModuleNotFoundError as error:
        if error.name != "display":
            raise  # a different module is missing: a real problem
        simple_view(maze, output_file)
        return
    MazeDisplay(maze, output_file).run()


def main() -> None:
    """Load the configuration and launch the maze interface."""
    try:
        if len(sys.argv) != 2:
            raise ConfigError(
                "usage: python3 a_maze_ing.py config.txt"
            )

        settings = load(sys.argv[1])
        maze = MazeGenerator(
            settings.width,
            settings.height,
            settings.entry,
            settings.exit,
            settings.perfect,
            settings.seed,
        )

        maze.generate()
        maze.write(settings.output_file)

        show(maze, settings.output_file)

    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
    except (ValueError, OSError) as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()