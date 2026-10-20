# A-Maze-ing: common tasks. Recipe lines must start with a real TAB.
#
# The development tools (flake8, mypy, build) live in a virtualenv (.venv).
# Each recipe line runs in its own shell, so the venv is never "activated":
# its Python is called directly instead.

PYTHON ?= python3
CONFIG ?= config.txt
VENV   := .venv
VPY    := $(VENV)/bin/python
# The program itself needs only the standard library: use the venv's Python
# when it exists, otherwise the system one (so `make run` works offline).
PY      = $(if $(wildcard $(VPY)),$(VPY),$(PYTHON))

.PHONY: install run debug clean fclean re lint lint-strict build

# Create the venv and install the tools. The marker file is written only
# once everything succeeded, so a failed install is retried next time and a
# finished one is not repeated.
install: $(VENV)/.installed

$(VENV)/.installed:
	$(PYTHON) -m venv $(VENV)
	$(VPY) -m pip install --upgrade pip
	$(VPY) -m pip install flake8 mypy build
	touch $@

run:
	$(PY) a_maze_ing.py $(CONFIG)

debug:
	$(PY) -m pdb a_maze_ing.py $(CONFIG)

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache
	rm -f maze.txt

# Everything clean removes, plus the venv and the build output. The
# mazegen-*.whl / .tar.gz at the root are submitted files and are kept.
fclean: clean
	rm -rf $(VENV) build dist *.egg-info

re:
	$(MAKE) fclean
	$(MAKE) install
	$(MAKE) run

lint: install
	$(VPY) -m flake8 .
	$(VPY) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict: install
	$(VPY) -m flake8 .
	$(VPY) -m mypy . --strict

# Rebuild the reusable package and copy it to the root of the repository.
build: install
	$(VPY) -m build
	cp dist/mazegen-*.whl dist/mazegen-*.tar.gz .