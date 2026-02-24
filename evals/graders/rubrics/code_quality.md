# Code Quality Rubric

For judging code produced by agents. Unit tests check if it works; this checks how it's written.

## What to check

**Correctness**
- Logically sound for the requirements
- Handles edge cases (empty, zero, negatives, etc.)
- No obvious runtime bugs

**Readability**
- Descriptive names
- Clear structure
- Consistent formatting

**Pythonic** (for Python)
- Uses idioms effectively
- No unnecessary verbosity
- Leverages built-ins

**Documentation**
- Purpose clear from signature/docstring
- Complex logic has comments
- Understandable without context

**Completeness**
- Includes all requested parts
- Examples/tests where helpful
- States assumptions

## Score
- **1.0** - Production-ready: clean, correct, idiomatic
- **0.7** - Works well, minor style issues
- **0.4** - Functional but rough
- **0.0** - Broken, unreadable, or incomplete
