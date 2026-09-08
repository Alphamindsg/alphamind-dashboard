"""Compatibility entry point for the dependency-free gateway checks."""

from notification_gateway.test_gateway import GatewayTests
import unittest


if __name__ == "__main__":
    unittest.main(defaultTest="GatewayTests")
