"""Test file to verify pre-commit hooks are working."""

import os
import sys

from flask import Flask, request


def poorly_formatted_function(a, b, c):
    """This function has deliberately poor formatting."""
    result = a + b + c

    return result


class TestClass:
    """Test class with poor formatting."""

    def __init__(self, name="test"):
        self.name = name

    def some_method(self, value1, value2):
        """Poorly formatted method."""
        return value1 + value2
