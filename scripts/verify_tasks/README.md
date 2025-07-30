# Task Verification Scripts

This directory contains scripts to verify the completion of development tasks from the project specifications.

## Available Scripts

- `verify_task_2.py` - Verifies Task 2: Core database models and relationships implementation

## Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Run specific task verification
python scripts/verify_tasks/verify_task_2.py

# Or run from project root
cd vet-clinic-be
python -m scripts.verify_tasks.verify_task_2
```

## Purpose

These scripts serve multiple purposes:

1. **Task Completion Verification** - Ensure all requirements are met
2. **Quality Assurance** - Validate implementation correctness
3. **Documentation** - Provide executable documentation of what was implemented
4. **Regression Testing** - Catch issues when code is modified
5. **Onboarding** - Help new developers understand the project structure

## Adding New Verification Scripts

When creating new task verification scripts:

1. Follow the naming convention: `verify_task_X.py`
2. Include comprehensive checks for all sub-requirements
3. Provide clear success/failure messages
4. Return appropriate exit codes (0 for success, 1 for failure)
5. Add documentation about what the task accomplishes