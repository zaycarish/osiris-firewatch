"""Automated tests for the optional VPN monitor."""

import unittest

from osiris.vpn.providers.base import CommandResult
from osiris.vpn.providers.windscribe import WindscribeAdapter


class TestWindscribeAdapter(unittest.TestCase):

    def test_connected_and_firewall_enabled(self):
        def fake_command(args):
            return CommandResult(
                0,
                "Connect state: Connected: New York - Empire\n"
                "Firewall state: On\n",
                "",
            )

        adapter = WindscribeAdapter(fake_command)

        self.assertTrue(adapter.check_connection({}).ok)
        self.assertTrue(adapter.check_firewall({}).ok)

    def test_disconnected(self):
        def fake_command(args):
            return CommandResult(
                0,
                "Connect state: Disconnected\nFirewall state: Off\n",
                "",
            )

        adapter = WindscribeAdapter(fake_command)

        self.assertFalse(adapter.check_connection({}).ok)
        self.assertFalse(adapter.check_firewall({}).ok)

    def test_cli_failure(self):
        def fake_command(args):
            return CommandResult(1, "", "CLI unavailable")

        adapter = WindscribeAdapter(fake_command)

        self.assertFalse(adapter.check_connection({}).ok)
        self.assertFalse(adapter.check_firewall({}).ok)


if __name__ == "__main__":
    unittest.main()


class TestWireGuardAdapter(unittest.TestCase):

    def test_successful_handshake(self):
        from osiris.vpn.providers.wireguard import WireGuardAdapter

        def fake_command(args):
            return CommandResult(0, "peer123 1700000000\n", "")

        adapter = WireGuardAdapter(fake_command)
        result = adapter.check_connection({"interface": "wg0"})

        self.assertTrue(result.ok)

    def test_no_handshake(self):
        from osiris.vpn.providers.wireguard import WireGuardAdapter

        def fake_command(args):
            return CommandResult(0, "peer123 0\n", "")

        adapter = WireGuardAdapter(fake_command)
        result = adapter.check_connection({"interface": "wg0"})

        self.assertFalse(result.ok)

    def test_command_failure(self):
        from osiris.vpn.providers.wireguard import WireGuardAdapter

        def fake_command(args):
            return CommandResult(1, "", "interface not found")

        adapter = WireGuardAdapter(fake_command)
        result = adapter.check_connection({"interface": "wg0"})

        self.assertFalse(result.ok)


class TestOpenVPNAdapter(unittest.TestCase):

    def test_active_service(self):
        from osiris.vpn.providers.openvpn import OpenVPNAdapter

        def fake_command(args):
            return CommandResult(0, "active\n", "")

        adapter = OpenVPNAdapter(fake_command)
        result = adapter.check_connection({
            "service_unit": "openvpn-client@test.service"
        })

        self.assertTrue(result.ok)

    def test_inactive_service(self):
        from osiris.vpn.providers.openvpn import OpenVPNAdapter

        def fake_command(args):
            return CommandResult(3, "inactive\n", "")

        adapter = OpenVPNAdapter(fake_command)
        result = adapter.check_connection({
            "service_unit": "openvpn-client@test.service"
        })

        self.assertFalse(result.ok)

    def test_command_failure(self):
        from osiris.vpn.providers.openvpn import OpenVPNAdapter

        def fake_command(args):
            return CommandResult(1, "", "service not found")

        adapter = OpenVPNAdapter(fake_command)
        result = adapter.check_connection({
            "service_unit": "openvpn-client@test.service"
        })

        self.assertFalse(result.ok)


class TestGenericAdapter(unittest.TestCase):

    def test_generic_registration(self):
        from osiris.vpn.providers import create_adapter
        from osiris.vpn.providers.generic import GenericAdapter

        adapter = create_adapter(
            "generic",
            lambda args: CommandResult(0, "", ""),
        )

        self.assertIsInstance(adapter, GenericAdapter)

    def test_generic_capabilities(self):
        from osiris.vpn.providers.generic import GenericAdapter

        adapter = GenericAdapter(
            lambda args: CommandResult(0, "", "")
        )

        self.assertFalse(adapter.supports("connection"))
        self.assertFalse(adapter.supports("firewall"))

    def test_generic_rejects_connection_check(self):
        from osiris.vpn.monitor import run_checks

        config = {
            "provider": "generic",
            "interface": "tun0",
            "checks": {
                "connection": True,
                "interface": False,
                "routes": False,
                "firewall": False,
            },
        }

        with self.assertRaises(ValueError):
            run_checks(
                config,
                lambda args: CommandResult(0, "", ""),
            )


class TestVPNInterface(unittest.TestCase):

    def test_interface_up(self):
        from osiris.vpn.system_checks import check_interface

        def fake_command(args):
            return CommandResult(
                0, "5: tun0: <POINTOPOINT,UP,LOWER_UP> mtu 1500\n", ""
            )

        self.assertTrue(check_interface(fake_command, "tun0").ok)

    def test_interface_down(self):
        from osiris.vpn.system_checks import check_interface

        def fake_command(args):
            return CommandResult(
                0, "5: tun0: <POINTOPOINT> mtu 1500\n", ""
            )

        self.assertFalse(check_interface(fake_command, "tun0").ok)

    def test_interface_missing(self):
        from osiris.vpn.system_checks import check_interface

        def fake_command(args):
            return CommandResult(1, "", "Device does not exist")

        self.assertFalse(check_interface(fake_command, "tun0").ok)


class TestVPNRoutes(unittest.TestCase):

    def test_correct_route(self):
        from osiris.vpn.system_checks import check_routes

        def fake_command(args):
            return CommandResult(
                0, "1.1.1.1 dev tun0 src 10.0.0.2\n", ""
            )

        result = check_routes(fake_command, "tun0", ["1.1.1.1"])
        self.assertTrue(result.ok)

    def test_route_bypasses_vpn(self):
        from osiris.vpn.system_checks import check_routes

        def fake_command(args):
            return CommandResult(
                0, "1.1.1.1 via 10.0.0.1 dev enp2s0\n", ""
            )

        result = check_routes(fake_command, "tun0", ["1.1.1.1"])
        self.assertFalse(result.ok)

    def test_route_missing(self):
        from osiris.vpn.system_checks import check_routes

        def fake_command(args):
            return CommandResult(2, "", "Network is unreachable")

        result = check_routes(fake_command, "tun0", ["1.1.1.1"])
        self.assertFalse(result.ok)
