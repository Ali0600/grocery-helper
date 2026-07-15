"""Shared pytest configuration.

Hypothesis profiles: CI must be deterministic (a randomized red would be an untrusted
gate), so `ci.yml` sets HYPOTHESIS_PROFILE=ci which derandomizes every property test.
Locally the default profile explores normally, and `hunt` digs deep before a PR:

    HYPOTHESIS_PROFILE=hunt python -m pytest -q tests/test_properties.py

Every bug a hunt finds gets pinned as a plain example-based test with the real
counterexample, so the regression coverage never depends on randomness.
"""
import os

from hypothesis import settings

settings.register_profile("ci", derandomize=True, max_examples=60)
settings.register_profile("default", max_examples=200)
settings.register_profile("hunt", max_examples=3000)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
