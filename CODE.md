# Code style instructions for the assistant

This document is a self-contained description of the owner's Python and
PyQt6 coding style. Apply it without needing any parent directory, example
project, or other document. Preserve these preferences even when you would
normally choose a different convention.

## Priorities

Follow the user's current instructions first. Otherwise, use the rules in
this document. Preserve required external interfaces and working behavior.
When a detail is not covered here, choose a simple, readable implementation
and keep it consistent within the module.

The strict personal preferences are double quotes, camelCase functions and
methods, complete import statements without parentheses, and no pointless
function reassignment or aliases. Follow PEP 8 for other formatting. These
personal preferences take priority where they differ from standard advice.

The intended feel is practical student-written Python: direct widget setup,
plain attributes, short understandable handlers, and little ceremony. Do not
turn a small task into a production framework. Existing code that differs
from these rules does not automatically establish a new preference.

## Formatting

- Use four spaces for indentation and otherwise follow PEP 8, subject to the
  owner's explicit exceptions below.
- Use double quotes for Python strings, including dictionary keys, f-strings,
  file paths, empty strings, and the main guard. Use triple double quotes for
  multiline strings and docstrings.
- Keep two blank lines around top-level classes and functions, and one blank
  line between methods. Separate meaningful steps with a blank line.
- Keep ordinary lines within 79 characters where practical. Wrap calls,
  expressions, and collections using implicit continuation.
- Do not pad code with decorative separators, redundant parentheses, or
  comments describing every obvious statement.
- Do not reformat unrelated code just to make the whole repository uniform.

## Imports: complete statements on individual lines

Never use parentheses or backslash continuation for imports. Several names
from the same module may share one line. If that line is too long, repeat
the `from` statement on another line:

```python
import csv
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget
```

Use separate statements for different imported modules. Import only what is
needed. Group standard-library, third-party, and local imports sensibly, with
blank lines between groups when useful. Keeping imports without parentheses
takes priority over a formatter's preferred multiline import layout.

## Names

- Write new functions and methods in camelCase: `loadData`, `showResults`,
  `addContact`, `findFilm`, `fillTable`, `toggleRecording`.
- Use the spelling `initUI` for window setup. Do not rename it
  to `init_ui` or create another setup method solely for naming consistency.
- Keep Python special methods and framework overrides exactly as required:
  `__init__`, `paintEvent`, `closeEvent`, `rowCount`, `headerData`, etc.
- Preserve names explicitly required by an exercise or external interface,
  even when they use snake_case, such as `get_result(name)`. Define the
  required name directly instead of adding an alias at the end.
- Use PascalCase for classes. Simple names such as `Example`, `MyWidget`,
  `MainWindow`, or the task's required class name are acceptable.
- Constants use uppercase names: `SCREEN_SIZE`, `NAME`, `HOTKEY`, `W`, `H`.
- Variables and attributes may use snake_case or camelCase: `filtered_rows`
  and `rowNumber` are both acceptable. Keep related names consistent within
  a module. The camelCase function rule does not require renaming every
  variable. CamelCase is a natural choice for Qt widget attributes.
- Short names such as `app`, `ex`, `btn`, `lbl`, `row`, `col`, `con`, `i`,
  `x`, `y`, `k`, and `n` are acceptable when the context makes them clear.
  Do not expand them into long formal names just for appearance.
- Qt Designer names such as `pushButton`, `lineEdit_2`, `tableWidget`, and
  `comboBox` are valid. Keep required attributes and object names intact.
- Preserve existing public names and unusual spellings when editing working
  code; do not introduce intentional spelling mistakes in new names.

## Keep the implementation direct

Prefer the straightforward solution that a student can explain line by line.
Use ordinary lists, dictionaries, tuples, loops, conditionals, and a few
methods. A modest amount of repetition is acceptable when it keeps a small
exercise easy to read.

Do not automatically introduce type annotations, dataclasses, protocols,
abstract base classes, dependency injection, factories, service containers,
or custom exception hierarchies. Default to unannotated methods and plain
instance attributes. Add machinery only when the task actually needs it.

Keep related operations together. A handler can read a widget, convert its
value, calculate a result, and update the interface directly. Extract a helper
when it has a clear purpose or removes substantial repetition; do not split
every two statements into a method.

Simple comprehensions, `enumerate`, `zip`, `sorted`, sets, and f-strings fit
this style. Use an ordinary loop when a comprehension becomes hard
to follow. A short lambda for sorting or a Qt signal is fine; elaborate
functional chains are not the default.

Do not add useless assignments that rename functions or methods at the end
of a file. Do not add several alternative attribute names for the same widget
to guess what a hidden test might expect. Use the actual required name.
Do not invent compatibility tricks, monkey patches, or custom string
comparison classes to work around guessed test expectations.

## Qt window structure

The usual exercise structure is imports, optional constants, a window class,
and a main guard. Start `__init__` with `super().__init__()`, initialize needed
state, and call `self.initUI()`. Put the interface setup in `initUI`, followed
by action handlers and other methods in a readable order.

Create widgets directly and configure them with ordinary method calls. Keep
each widget's creation, size, position, and signal connection close together.
Store widgets on `self` when handlers need them; temporary labels and layouts
can remain local variables. Keep non-modal child windows on `self` so they
remain alive.

Explicit coordinates are normal here. `setGeometry`, `move`, `resize`, and
`setFixedSize` are acceptable even if a layout would be more flexible. Do not
replace working manual placement just because layouts are usually recommended.
Layouts are equally acceptable when appropriate for the task. For an existing
window, preserve its approach unless changing it is part of the request.

Connect signals directly, for example:

```python
self.resultButton.clicked.connect(self.showResults)
self.slider.valueChanged.connect(self.update)
```

Use `self.sender()` or a `QButtonGroup` when it makes a shared handler simple.
When binding loop values in lambdas, capture the current value explicitly.
Use PyQt6 enum spellings such as `Qt.AlignmentFlag.AlignCenter` and
`Qt.Orientation.Horizontal`.

For drawing tasks, keep drawing in `paintEvent`, use `QPainter`, and call
`self.update()` when the state changes. Do not introduce a separate rendering
framework for a small drawing exercise.

When a task uses Qt Designer, load its supplied `.ui` with
`uic.loadUi(filename, self)` and use its object names. Do not require a new
Designer file for an exercise that is already implemented entirely in Python.

User-facing titles, labels, buttons, and error messages are normally in Russian.
Preserve the exact wording and output format required by an exercise.

## Program entry point

For a standalone GUI exercise, use this familiar pattern:

```python
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())
```

`window` instead of `ex` is also acceptable. Do not add
a `main()` wrapper merely to make this small block look more formal. A task
that asks only for a function should contain that function and needed imports,
without an unrelated GUI or demonstration run.

## Validation and errors

Keep validation close to the action. Early returns for empty input, cancelled
dialogs, missing selections, or invalid numbers fit this style.
Use `try`/`except` around conversions and operations that can fail, and report
errors through the window's existing label, status bar, or message box.

Do not build a validation framework or add speculative fallback paths for
every possible input type. A silent return is acceptable when the task calls
for ignoring an invalid action. Otherwise, give useful feedback through the
interface. Catch relevant exception types where they are known; do not hide
unrelated failures in a broad `except Exception` just to keep the code short.

## Files, CSV, SQLite, and tables

- Use `with open(..., encoding="utf-8") as file` for text files. For CSV,
  use the standard `csv` module and the delimiter required by the data;
  use `newline=""` when appropriate.
- Keep small datasets as lists of rows and headers. Do not introduce pandas
  or another dependency for an exercise handled by `csv` and loops.
- Use `sqlite3` directly. Names such as `con`, `connection`, and `cursor`
  are all acceptable. Write SQL keywords in uppercase.
- Use `?` placeholders and separate parameters for SQL values, including a
  trailing comma for a one-element tuple. Use triple double quotes for longer
  SQL statements. Do not copy raw SQL interpolation into ordinary value input
  just because a query-building exercise accepts SQL fragments.
- Save database changes with a transaction context or an explicit `commit()`.
  Close persistent connections when their owner is finished with them.
- Populate `QTableWidget` with row and column loops and `QTableWidgetItem`.
  Convert values to strings where needed. Use a table model when the task
  calls for one or the current code already uses one.

## Resource paths and module boundaries

Treat the opened project directory as an independent project. Do not depend
on its original location, parent directories, sibling projects, or absolute
paths from the developer's machine. Internal imports should use the project's
own module structure and support its intended launch command.

For application-owned resources, build paths relative to the relevant module
or an explicit project resource directory when they must work independently
of the current working directory. User-selected files should use the paths
returned by the dialog. Avoid speculative searches through unrelated folders.

For a Yandex LMS submission, use only the filenames and resources specified
by the assignment. Keep a single-file submission self-contained when required;
local organizational folders are not part of the submission environment.

For a multi-file application, separate modules by their actual responsibilities:
startup, shared configuration, windows, storage, recording, recognition, API
requests, and utilities as needed. Keep a simple task in one file when that
is enough. Do not create empty abstraction layers to anticipate future work.

Database and service code should not create windows. Long recognition,
network, or other blocking operations should run in a worker and report back
through Qt signals. Update widgets in the GUI thread. Keep this separation
without adding architectural layers beyond the actual project needs.

## Comments and final review

Comments should explain something non-obvious or required by the assignment.
Short Russian comments fit this style. Do not add a docstring to every
method, tutorial paragraphs to simple handlers, or decorative section banners.
Explain a complex algorithm when that explanation helps, without making long
explanations mandatory for ordinary code.

Before finishing a change, check that:

- New strings use double quotes and new methods use camelCase.
- Imports are complete lines without parenthesized lists.
- Existing required names, resources, and output wording still work.
- No pointless aliases, wrapper methods, or unrelated refactors were added.
- The code stays direct, readable, and proportional to the task.
- Any exception to PEP 8 comes from an explicit preference or required API,
  rather than accidental formatting.
