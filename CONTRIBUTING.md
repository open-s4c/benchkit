# Contributing to benchkit

Contributions are welcome.
Contact the [maintainer](MAINTAINERS) for more information.

### Source organization

Source organization is already documented for users in the [README](README.md).
As of August 2023, the code base is slowly reaching 10k of lines of python code.

### Modifying the core

The core is the `benchkit/` directory.   It defines everything required to run
campaigns and benchmarks, with lots of utility functions and classes.

### Add support for a benchmark

Supported benchmarks are placed in the `examples/` directory.

### Conventions

When defining a class, the following order of functions should be respected:

 1. `__new__` (static) method
 2. `__init__` method
 3. `__post_init__` method
 4. Properties (`@property`)
 5. Static methods (`@staticmethod`) 
 6. Class methods (`@classmethod`) 
 7. Normal methods 
 8. Protected or private methods (with the name starting with `_`)


### Check list to modify a python file

- if the file is executable, the shebang must be the first line: `#!/usr/bin/env python3`
- type hinting is correct & complete (to a _reasonable_ extent)
- sorting imports: `isort --profile black .`
- formatting: `black -l 100 .`
- checking: `pylint`
- checking: `flake8`

### Reviews

All contributions require to be reviewed by the [maintainer](MAINTAINERS).
