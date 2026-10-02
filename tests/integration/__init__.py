"""
Integration tests for CFB League Bot

These tests make REAL HTTP requests to external services:
- On3.com for recruiting data
- MaxPreps for HS stats
- CFB Data API for college stats

They are useful for:
1. Verifying scrapers still work with current website structure
2. Testing with real player data
3. Detecting when sites change their HTML structure

Run with: pytest tests/integration/ -v
These tests require network access and may be slower.

Mark: @pytest.mark.integration
"""
