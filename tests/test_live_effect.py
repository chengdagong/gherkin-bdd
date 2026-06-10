"""Binds the BDD-rule effect scenarios (all @agent) to the live steps in conftest.

Run on demand: .venv/bin/pytest -m "agent and not todo"
"""

from pytest_bdd import scenarios

scenarios("../features/bdd-rule-effect.feature")
