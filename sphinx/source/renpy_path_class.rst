RenpyPath
=========

RenpyPath provides a `PathLike <https://docs.python.org/3/library/os.html#os.PathLike>`_-style
way to work with game files, analogous to
`pathlib.PurePath <https://docs.python.org/3/library/pathlib.html#pure-paths>`_
plus some methods from `Path <https://docs.python.org/3/library/pathlib.html#pathlib.Path>`_.
The files are discovered using Ren'Py's standard search method,
and may reside in the game directory, in an RPA archive, as an Android
asset, in a remote server, or in any additional location a plugin may
provide.

Use :func:`renpy.list_files` when you want a full flat listing.
Use ``RenpyPath`` when you want to navigate a subset of directories or
perform tree-like operations over Ren'Py files.

.. include:: inc/renpy_path

Usage Examples
--------------

**Find eileen's image files by pattern:**

.. code-block:: python

    init python:
        eileen_images = list(RenpyPath("images").rglob("eileen_*.{avif,{jp{,e}g}},png,webp"))

**Create a file in the game directory relative to another:**

.. code-block:: python

    init python:
        commentary_path = RenpyPath("comments")
        (commentary_path / f'comment_{next_comment_number}.txt').as_path().write_text(comment)

**Read a file relative to the current script:**

.. code-block:: python

    init python:
        here, _line = RenpyPath.current_path_line()
        data_text = (here.parent / "my_data.txt").read_text()

**Exclude current script and its compiled file from builds:**

.. code-block:: python

    init python:
        here, _line = RenpyPath.current_path_line()
        here.rpy_path().build_classify(None)
        here.rpyc_path().build_classify(None)

**Replace loadable + open_file with RenpyPath:**

.. code-block:: python

    init python:
        with RenpyPath("data/config.txt").open() as f:
            for line in f:
                pass

**Read a JSON file:**

.. code-block:: python

    init python:
        import json
        with RenpyPath("data/config.json").open("r", encoding="utf-8") as f:
            data = json.load(f)


