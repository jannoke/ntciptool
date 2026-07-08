#!/usr/bin/env python3
"""ntciptool - Universal NTCIP VMS (Variable Message Sign) communication tool.

Protocol : SNMP v1/v2c (NTCIP 1203)
Features : Brightness control (dmsIllumControl)
"""

import sys
import argparse
from typing import Optional

try:
    from pysnmp.hlapi import (
        getCmd, setCmd,
        SnmpEngine, CommunityData, UdpTransportTarget,
        ContextData, ObjectType, ObjectIdentity, Integer32
    )
except ImportError:
    print("ERROR: pysnmp is required.  Install with:  pip install pysnmp", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# NTCIP 1203 OIDs
# ---------------------------------------------------------------------------
# dmsIllumControl  – controls the brightness source
# OBJECT-TYPE SYNTAX INTEGER { other(1), photocell(2), timer(3),
#                               manual(4), manualDirect(5), manualIndexed(6) }
OID_ILLUM_CONTROL = "1.3.6.1.4.1.1206.4.2.3.7.1"

BRIGHTNESS_MODES = {
    "other":         1,
    "photocell":     2,
    "timer":         3,
    "manual":        4,
    "manualdirect":  5,
    "manualindexed": 6,
}

BRIGHTNESS_NAMES = {v: k for k, v in BRIGHTNESS_MODES.items()}

DEFAULT_COMMUNITY_READ  = "public"
DEFAULT_COMMUNITY_WRITE = "administrator"
DEFAULT_PORT            = 161

# ---------------------------------------------------------------------------
# SNMP helpers
# ---------------------------------------------------------------------------

def snmp_get(host: str, oid: str, community: str = DEFAULT_COMMUNITY_READ,
             port: int = DEFAULT_PORT) -> Optional[int]:
    """Return the integer value of *oid* from *host*, or None on error."""
    error_indication, error_status, error_index, var_binds = next(
        getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),          # mpModel=1 → SNMPv2c
            UdpTransportTarget((host, port), timeout=3, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
    )
    if error_indication:
        print(f"  [GET error] {host}: {error_indication}", file=sys.stderr)
        return None
    if error_status:
        print(f"  [GET error] {host}: {error_status.prettyPrint()} at "
              f"{error_index and var_binds[int(error_index) - 1][0] or '?'}",
              file=sys.stderr)
        return None
    for _, val in var_binds:
        return int(val)
    return None


def snmp_set(host: str, oid: str, value: int,
             community: str = DEFAULT_COMMUNITY_WRITE,
             port: int = DEFAULT_PORT) -> bool:
    """Set *oid* to Integer32 *value* on *host*.  Return True on success."""
    error_indication, error_status, error_index, var_binds = next(
        setCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),
            UdpTransportTarget((host, port), timeout=3, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid), Integer32(value)),
        )
    )
    if error_indication:
        print(f"  [SET error] {host}: {error_indication}", file=sys.stderr)
        return False
    if error_status:
        print(f"  [SET error] {host}: {error_status.prettyPrint()} at "
              f"{error_index and var_binds[int(error_index) - 1][0] or '?'}",
              file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# Feature: brightness
# ---------------------------------------------------------------------------

def brightness_mode_label(value: Optional[int]) -> str:
    """Return a human-readable label for a dmsIllumControl integer value."""
    if value is None:
        return "(read error)"
    return BRIGHTNESS_NAMES.get(value, f"unknown({value})")


def cmd_brightness(hosts: list[str], args: argparse.Namespace) -> None:
    """Read or write dmsIllumControl on one or more signs."""
    new_mode: Optional[int] = None

    if args.mode is not None:
        key = args.mode.lower().replace("-", "").replace("_", "")
        if key not in BRIGHTNESS_MODES:
            print(f"ERROR: Unknown brightness mode '{args.mode}'.  "
                  f"Valid values: {', '.join(BRIGHTNESS_MODES)}", file=sys.stderr)
            sys.exit(1)
        new_mode = BRIGHTNESS_MODES[key]

    for host in hosts:
        print(f"\n{'─' * 60}")
        print(f"  Host : {host}")

        # ── READ CURRENT VALUE ────────────────────────────────────────────
        before = snmp_get(host, OID_ILLUM_CONTROL,
                          community=args.read_community, port=args.port)
        print(f"  Brightness (before) : {brightness_mode_label(before)} [{before}]")

        if new_mode is None:
            # Status-only – nothing more to do
            continue

        # ── WRITE NEW VALUE ───────────────────────────────────────────────
        print(f"  Setting brightness  : {brightness_mode_label(new_mode)} [{new_mode}]")
        ok = snmp_set(host, OID_ILLUM_CONTROL, new_mode,
                      community=args.write_community, port=args.port)
        if not ok:
            print("  Result              : FAILED")
            continue

        # ── VERIFY NEW VALUE ──────────────────────────────────────────────
        after = snmp_get(host, OID_ILLUM_CONTROL,
                         community=args.read_community, port=args.port)
        print(f"  Brightness (after)  : {brightness_mode_label(after)} [{after}]")

        if after == new_mode:
            print("  Result              : OK ✓")
        else:
            print(f"  Result              : MISMATCH – expected {new_mode}, got {after}")

    print(f"\n{'─' * 60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ntciptool",
        description=(
            "Universal NTCIP / SNMP tool for Variable Message Signs (VMS).\n\n"
            "Multiple IP addresses may be supplied; the tool will operate on each\n"
            "in sequence and display before/after status when writing values."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Show brightness mode on two signs\n"
            "  ntciptool brightness 192.168.1.10 192.168.1.11\n\n"
            "  # Set brightness to photocell on one sign\n"
            "  ntciptool brightness --mode photocell 192.168.1.10\n\n"
            "  # Set brightness to manual on three signs with custom communities\n"
            "  ntciptool brightness --mode manual \\\n"
            "           --write-community admin \\\n"
            "           192.168.1.10 192.168.1.11 192.168.1.12\n"
        ),
    )

    # ── global options ────────────────────────────────────────────────────
    parser.add_argument("-p", "--port",
                        type=int, default=DEFAULT_PORT,
                        metavar="PORT",
                        help="SNMP UDP port (default: 161)")
    parser.add_argument("-r", "--read-community",
                        default=DEFAULT_COMMUNITY_READ,
                        metavar="COMMUNITY",
                        help="SNMP read community string (default: public)")
    parser.add_argument("-w", "--write-community",
                        default=DEFAULT_COMMUNITY_WRITE,
                        metavar="COMMUNITY",
                        help="SNMP write community string (default: administrator)")

    subparsers = parser.add_subparsers(dest="command", title="commands")

    # ── brightness sub-command ────────────────────────────────────────────
    brightness_parser = subparsers.add_parser(
        "brightness",
        help="Get or set dmsIllumControl (brightness source)",
        description=(
            "Read or change the brightness control mode of one or more signs.\n\n"
            "Brightness modes (dmsIllumControl):\n"
            "  other         (1) – vendor-specific behaviour\n"
            "  photocell     (2) – automatic via photocell sensor\n"
            "  timer         (3) – scheduled timer\n"
            "  manual        (4) – manual indexed level via dmsIllumManLevel\n"
            "  manualDirect  (5) – direct light output percentage\n"
            "  manualIndexed (6) – indexed via separate control table\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    brightness_parser.add_argument(
        "--mode", "-m",
        choices=list(BRIGHTNESS_MODES.keys()),
        metavar="MODE",
        help=(
            "Brightness mode to set. "
            f"Choices: {', '.join(BRIGHTNESS_MODES)}. "
            "Omit to read current value only."
        ),
    )
    brightness_parser.add_argument(
        "hosts",
        nargs="+",
        metavar="IP",
        help="IP address(es) of target VMS sign(s)",
    )

    return parser


def main() -> None:
    parser = build_parser()

    # Print help when called with no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "brightness":
        cmd_brightness(args.hosts, args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
