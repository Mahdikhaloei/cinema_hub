from datetime import datetime


class MockableDatetime(datetime):
    """Create a subclass of python's built-in datetime, so we can mock it"""
    pass
