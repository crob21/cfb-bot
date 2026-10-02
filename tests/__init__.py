"""
CFB League Bot Test Suite

Test Categories:
- unit/: Fast tests that mock external dependencies
- integration/: Slower tests that make real HTTP requests
- fixtures/: Shared test data and mock objects

Run all tests:
    pytest tests/ -v

Run only unit tests (fast):
    pytest tests/unit/ -v

Run only integration tests (requires network):
    pytest tests/integration/ -v

Run with coverage:
    pytest tests/ --cov=src/cfb_bot --cov-report=html

Skip slow integration tests:
    pytest tests/ -v -m "not integration"
"""
