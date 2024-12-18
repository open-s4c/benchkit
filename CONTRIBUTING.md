# Contributing to benchkit

Contributions are welcome.
Contact the [maintainer](MAINTAINERS) for more information.

## Source organization

Source organization is already documented in the [README](README.md).
As of December 2024, the codebase is over 21k lines of Python code.

## Modifying the core

The core of the project is in the `benchkit/` directory.
It defines everything required to run campaigns and benchmarks, including
utility functions and classes.

## Adding support for a benchmark

Supported benchmarks are placed in the `examples/` directory.

## Conventions

When defining a class, follow this order for methods:

1. `__new__` (static) method
2. `__init__` method
3. `__post_init__` method
4. Properties (`@property`)
5. Static methods (`@staticmethod`)
6. Class methods (`@classmethod`)
7. Regular methods
8. Protected or private methods (prefix `_`)

## Checklist for modifying a Python file

- **Shebang**: Executable files must start with `#!/usr/bin/env python3`.
- **Type Hinting**: Ensure type annotations are correct and reasonably complete.
- **Imports**: Sort using `isort --profile black .`.
- **Formatting**: Apply `black -l 100 .`.
- **Linting**: Run `pylint` and `flake8` to catch errors and maintain style
  consistency.

A helper script is provided to apply these, you can invoke it as follows:

```bash
BENCHKIT_NO_PYLINT=yes ./scripts/all_checks.sh
```

## Copyright attribution policy

### General Guidelines

1. **New Files**: Copyright should be attributed to the contributor's current
   organization or individual name, as applicable.
2. **Minor Modifications**: Leave the existing copyright unchanged.
3. **Significant Modifications**: Add a new copyright line to the modified file.
4. **LICENSE File Updates**: If significant modifications span multiple files,
   update the LICENSE file to reflect the added copyright.

### Contributors

- If contributing as an individual, use:
  `Copyright (C) [year] [Your Name].`
- If contributing on behalf of an organization, follow its attribution
  guidelines.

For questions, consult the [maintainer](MAINTAINERS).

## Reviews

All contributions must be reviewed and approved by the [maintainer](MAINTAINERS).
