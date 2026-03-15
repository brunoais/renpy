File Access
===========

These Python functions allow you to access asset files, which may be found
in the game directory, RPA archives, or as Android assets.

.. include:: inc/file

RenpyPath
---------

RenpyPath provides a `PathLike <https://docs.python.org/3/library/os.html#os.PathLike>`_-style
way to work with game files, with all methods and attributes of
`pathlib.PurePath <https://docs.python.org/3/library/pathlib.html#pure-paths>`_
and some methods of `Path <https://docs.python.org/3/library/pathlib.html#pathlib.Path>`_
. Use it when you want to navigate a subset of directories or
perform tree-like operations over Ren'Py files without juggling filename
strings.

RenpyPath is detailed in its own page at :doc:`renpy_path_class`.

Rarely Used
-----------

These functions are used more rarely.

.. include:: inc/file_rare
