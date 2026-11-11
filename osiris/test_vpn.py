"""Tests for the optional, read-only VPN monitor."""

import unittest

from osiris.vpn.monitor import run_checks
from osiris.vpn.providers.base import CommandResult


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, command):
        command = tuple(command)
        self.calls.append(command)
        for prefix, response in self.responses:
            if command[:len(prefix)] == prefix:
                return response
        return CommandResult(127, "", f"unexpected command: {command}")


class VPNMonitorTests(unittest.TestCase):
    def test_windscribe_all_checks_pass(self):
        runner = FakeRunner([
            (
                ("/usr/bin/windscribe-cli", "status"),
                CommandResult(
                    0,
                    "Connect state: Connected: Test\nFirewall state: On",
                    "",
                ),
            ),
            (
                ("ip", "-o", "link"),
                CommandResult(
                    0,
                    "7: tun0: <POINTOPOINT,UP,LOWER_UP> mtu 1500",
                    "",
                ),
            ),
            (
                ("ip", "-4", "route", "get"),
                CommandResult(0, "1.1.1.1 dev tun0 src 10.0.0.2", ""),
            ),
        ])
        config = {
            "provider": "windscribe",
            "interface": "tun0",
            "route_targets": ["1.1.1.1"],
            "checks": {
                "connection": True,
                "interface": True,
                "routes": True,
                "firewall": True,
            },
        }

        results = run_checks(config, runner)

        self.assertTrue(all(result.ok for result in results))
        status_calls = [
            call for call in runner.calls
            if call == ("/usr/bin/windscribe-cli", "status")
        ]
        self.assertEqual(len(status_calls), 1)

    def test_openvpn_rejects_unsupported_firewall_check(self):
        config = {
            "provider": "openvpn",
            "checks": {
                "connection": False,
                "interface": False,
                "routes": False,
                "firewall": True,
            },
        }

        with self.assertRaisesRegex(ValueError, "does not support"):
            run_checks(config, FakeRunner([]))

    def test_wireguard_accepts_completed_handshake(self):
        runner = FakeRunner([
            (
                ("/usr/bin/wg", "show", "wg0", "latest-handshakes"),
                CommandResult(0, "peer-key 1700000000", ""),
            ),
        ])
        config = {
            "provider": "wireguard",
            "interface": "wg0",
            "checks": {
                "connection": True,
                "interface": False,
                "routes": False,
                "firewall": False,
            },
        }

        results = run_checks(config, runner)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)

    def test_route_check_detects_wrong_interface(self):
        runner = FakeRunner([
            (
                ("ip", "-4", "route", "get"),
                CommandResult(0, "1.1.1.1 dev eth0 src 192.0.2.2", ""),
            ),
        ])
        config = {
            "provider": "windscribe",
            "interface": "tun0",
            "route_targets": ["1.1.1.1"],
            "checks": {
                "connection": False,
                "interface": False,
                "routes": True,
                "firewall": False,
            },
        }

        results = run_checks(config, runner)

        self.assertFalse(results[0].ok)
        self.assertIn("1.1.1.1", results[0].detail)


    def test_generic_provider_uses_interface_and_routes(self):
        runner = FakeRunner([
            (
                ("ip", "-o", "link"),
                CommandResult(
                    0,
                    "9: vpn0: <POINTOPOINT,UP,LOWER_UP> mtu 1500",
                    "",
                ),
            ),
            (
                ("ip", "-4", "route", "get"),
                CommandResult(0, "1.1.1.1 dev vpn0 src 10.8.0.2", ""),
            ),
        ])
        config = {
            "provider": "generic",
            "interface": "vpn0",
            "route_targets": ["1.1.1.1"],
            "checks": {
                "connection": False,
                "interface": True,
                "routes": True,
                "firewall": False,
            },
        }

        results = run_checks(config, runner)

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.ok for result in results))


if __name__ == "__main__":
    unittest.main()
