#!/usr/bin/env python3
"""
Miko3 Talents Automation Framework -- CLI Runner
=================================================
Main entry point for running talent tests, discovery, and analysis.

Usage:
    # Run all tests
    python runner.py --all

    # Run specific talent
    python runner.py --talent video
    python runner.py --talent storymaker
    python runner.py --talent storytelling
    python runner.py --talent adventure_book

    # Test a third-party talent
    python runner.py --talent thirdparty --package com.example.app

    # Discover installed talents
    python runner.py --discover

    # Show RICE POT analysis
    python runner.py --rice

    # Advanced options
    python runner.py --all --device 192.168.1.100:5555 --config custom.yaml --verbose
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional, List

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import yaml

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from miko3_automation.core.adb_utils import ADBClient, ADBError, ConnectionError
from miko3_automation.core.device_manager import DeviceManager, DeviceNotFoundError
from miko3_automation.core.connection_monitor import (
    ConnectionMonitor,
    ResilientADBClient,
)
from miko3_automation.core.checkpoint import CheckpointManager
from miko3_automation.core.talent_discovery import TalentDiscovery
from miko3_automation.talents.video_talent import VideoTalentTest
from miko3_automation.talents.storymaker_talent import StorymakerTalentTest
from miko3_automation.talents.vooks_talent import VooksTalentTest
from miko3_automation.talents.thirdparty_talent import ThirdPartyTalentTest
from miko3_automation.talents.adventure_book_talent import AdventureBookTalentTest
from miko3_automation.verification.verifier import Verifier
from miko3_automation.reporting.html_report import HTMLReportGenerator
from miko3_automation.rice_pot.analyzer import RICEPOTAnalyzer


def load_config(config_path: str) -> dict:
    """Load YAML configuration."""
    if not os.path.exists(config_path):
        print(f"[ERROR] Config file not found: {config_path}")
        print("  Using default configuration.")
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def setup_logging(verbose: bool, config: dict) -> None:
    """Configure logging."""
    log_cfg = config.get("logging", {})
    level = (
        logging.DEBUG
        if verbose
        else getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    )

    # Create log directory
    log_file = log_cfg.get("log_file", "reports/automation.log")
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if log_cfg.get("console_output", True):
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def print_banner():
    """Print the framework banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║           🤖 Miko3 Talents Automation Framework             ║
║                    ADB + Python + Verification              ║
║                         v1.0.0                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def cmd_discover(adb: ADBClient) -> None:
    """Discover and list all installed talents."""
    print("\n📡 Discovering installed talents...\n")
    discovery = TalentDiscovery(adb)

    # Miko talents
    print("── Miko Talents ─────────────────────────────────")
    miko_pkgs = discovery.find_miko_packages()
    if miko_pkgs:
        for pkg in miko_pkgs:
            info = discovery.get_talent_info(pkg)
            print(f"  ✓ {info.app_name:<30} {info.package}")
            print(f"    Activity: {info.main_activity}  |  Version: {info.version}")
    else:
        print("  (No Miko-specific packages found)")

    # Third-party talents
    print("\n── Third-Party Talents ──────────────────────────")
    tp_pkgs = discovery.list_all_packages(include_system=False)
    # Exclude miko packages
    tp_only = [p for p in tp_pkgs if p not in miko_pkgs]
    if tp_only:
        for pkg in tp_only[:30]:  # Limit display
            info = discovery.get_talent_info(pkg)
            print(f"  • {info.app_name:<30} {info.package}")
        if len(tp_only) > 30:
            print(f"  ... and {len(tp_only) - 30} more")
    else:
        print("  (No third-party packages found)")

    # Current foreground
    print("\n── Current Foreground ──────────────────────────")
    fg = discovery.get_foreground_talent()
    if fg:
        print(f"  ▶ {fg.app_name} ({fg.package})")
    else:
        print("  (Could not determine foreground app)")

    print(f"\n  Total: {len(miko_pkgs)} Miko + {len(tp_only)} third-party packages\n")


def cmd_rice(config: dict) -> None:
    """Show RICE POT prioritization analysis."""
    analyzer = RICEPOTAnalyzer(config)
    print(analyzer.generate_summary())

    # Show detailed justifications
    print("\n📋 DETAILED JUSTIFICATIONS:\n")
    for talent_key in [
        "video",
        "storymaker",
        "vooks",
        "thirdparty",
        "adventure_book",
    ]:
        score = analyzer.get_score(talent_key)
        justifications = analyzer.get_justifications(talent_key)
        if justifications:
            print(f"  {score.talent_name} (Score: {score.rice_score:.1f})")
            for dim, reason in justifications.items():
                print(f"    {dim.upper():<12}: {reason}")
            print()


def cmd_run_tests(
    adb: ADBClient,
    config: dict,
    talents: list,
    package: str = "",
    resume: bool = False,
    device_manager: Optional[DeviceManager] = None,
) -> list:
    """Run specified talent tests and return results with interruption handling."""
    results = []
    report = HTMLReportGenerator(config)
    checkpoint_mgr = CheckpointManager()

    # Initialize connection monitor
    connection_monitor: Optional[ConnectionMonitor] = None
    if device_manager:
        connection_monitor = ConnectionMonitor(adb, check_interval=5)

    # Map talent names to test classes
    talent_map = {
        "video": VideoTalentTest,
        "storymaker": StorymakerTalentTest,
        "vooks": VooksTalentTest,
        "adventure_book": AdventureBookTalentTest,
    }

    for talent_name in talents:
        print(f"\n🚀 Running: {talent_name.upper()} test...")
        print("─" * 50)

        # Check for checkpoint to resume from
        start_step = 0
        if resume and checkpoint_mgr.has_checkpoint(talent_name):
            checkpoint = checkpoint_mgr.load_checkpoint(talent_name)
            if checkpoint:
                start_step = checkpoint.get("state", {}).get("current_step", 0)
                print(f"  📍 Resuming from checkpoint (step {start_step})")

        try:
            if talent_name == "thirdparty":
                if not package:
                    print("  [SKIP] No --package specified for third-party test")
                    continue
                test = ThirdPartyTalentTest(
                    adb=adb,
                    config=config,
                    package_name=package,
                    checkpoint_name=talent_name,
                )
            elif talent_name in talent_map:
                test = talent_map[talent_name](
                    adb=adb,
                    config=config,
                    checkpoint_name=talent_name,
                )
            else:
                print(f"  [SKIP] Unknown talent: {talent_name}")
                continue

            # Handle resume from checkpoint
            if start_step > 0 and hasattr(test, "resume_from_checkpoint"):
                checkpoint = checkpoint_mgr.load_checkpoint(talent_name)
                if checkpoint:
                    test.resume_from_checkpoint(checkpoint)

            result = test.run()
            results.append(result)
            report.add_result(result)

            # Clear checkpoint on successful completion
            if result.passed:
                checkpoint_mgr.clear_checkpoint(talent_name)

            # Print result summary
            status_icon = "✅" if result.passed else "❌"
            print(f"\n  {status_icon} {result.talent_name}: {result.status.value}")
            print(f"  Duration: {result.duration:.1f}s | {result.step_summary}")
            if result.error_message:
                print(f"  Error: {result.error_message}")

        except ConnectionError as e:
            print(f"  ⚠️ Connection lost: {e}")
            if connection_monitor and device_manager:
                print("  🔄 Attempting reconnection...")
                if device_manager.reconnect(max_attempts=3, delay=2.0):
                    print(
                        "  ✅ Reconnection successful, test will be resumed on next run"
                    )
                    checkpoint_mgr.save_checkpoint(
                        talent_name,
                        {
                            "current_step": start_step,
                            "step_name": "interrupted",
                            "error": str(e),
                        },
                    )
                else:
                    print("  ❌ Reconnection failed")
            print(f"  📍 Progress saved, run with --resume to continue")
            logging.getLogger(__name__).warning(
                "Connection lost in %s: %s", talent_name, e
            )

        except Exception as e:
            print(f"  ❌ FATAL ERROR in {talent_name}: {e}")
            logging.getLogger(__name__).exception("Fatal error in %s", talent_name)

    # Generate report
    if results:
        print("\n" + "═" * 50)
        print("📊 GENERATING REPORT...")
        report_path = report.generate()
        print(f"✅ Report saved: {os.path.abspath(report_path)}")

        # Print summary
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        print(f"\n📋 SUMMARY: {passed}/{total} passed, {failed} failed")
        print("═" * 50)

    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="🤖 Miko3 Talents Automation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py --all                          Run all talent tests
  python runner.py --talent video                 Test video talent only
  python runner.py --talent thirdparty --package com.example.app
  python runner.py --discover                     List installed talents
  python runner.py --rice                         Show RICE POT analysis
  python runner.py --all --verbose --device SERIAL
        """,
    )

    # Actions
    actions = parser.add_argument_group("Actions")
    actions.add_argument("--all", action="store_true", help="Run all talent tests")
    actions.add_argument(
        "--talent",
        choices=["video", "storymaker", "vooks", "thirdparty", "adventure_book"],
        action="append",
        help="Run specific talent test (can be repeated)",
    )
    actions.add_argument(
        "--discover", action="store_true", help="Discover installed talents"
    )
    actions.add_argument("--rice", action="store_true", help="Show RICE POT analysis")

    # Options
    options = parser.add_argument_group("Options")
    options.add_argument(
        "--package", type=str, default="", help="Third-party package name"
    )
    options.add_argument("--device", type=str, default="", help="Target device serial")
    options.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Config file path (default: config/config.yaml)",
    )
    options.add_argument(
        "--report-dir", type=str, default="", help="Report output directory"
    )
    options.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    options.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint if interrupted",
    )
    options.add_argument(
        "--clear-checkpoints",
        action="store_true",
        help="Clear all saved checkpoints before running",
    )

    args = parser.parse_args()

    # Require at least one action
    if not any([args.all, args.talent, args.discover, args.rice]):
        parser.print_help()
        print(
            "\n[ERROR] Specify at least one action: --all, --talent, --discover, or --rice"
        )
        sys.exit(1)

    # Load config
    config = load_config(args.config)

    # Override device serial from CLI
    if args.device:
        config.setdefault("device", {})["serial"] = args.device

    # Override report dir
    if args.report_dir:
        config.setdefault("reporting", {})["output_dir"] = args.report_dir

    # Setup logging
    setup_logging(args.verbose, config)
    logger = logging.getLogger(__name__)

    print_banner()
    print(f"  Config: {os.path.abspath(args.config)}")
    print(f"  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- RICE POT only (no device needed) ---
    if args.rice and not any([args.all, args.talent, args.discover]):
        cmd_rice(config)
        sys.exit(0)

    # --- Connect to device ---
    try:
        print("\n📱 Connecting to device...")
        dm = DeviceManager(config)
        adb = dm.get_device()
        dm.ensure_ready()

        info = dm.get_device_info()
        print(
            f"  ✓ Connected: {info.get('model', 'Unknown')} ({info.get('serial', '')})"
        )
        print(
            f"  Android: {info.get('android_version', '?')} | Battery: {info.get('battery_level', '?')}%"
        )

    except (DeviceNotFoundError, ADBError) as e:
        print(f"\n❌ Device connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Connect Miko3 via USB and enable USB Debugging")
        print("  2. Run: adb devices")
        print("  3. Check ADB is installed and in PATH")
        sys.exit(1)

    # --- Discover ---
    if args.discover:
        cmd_discover(adb)

    # --- RICE POT ---
    if args.rice:
        cmd_rice(config)

    # --- Run Tests ---
    if args.all or args.talent:
        # Clear checkpoints if requested
        if args.clear_checkpoints:
            checkpoint_mgr = CheckpointManager()
            cleared = checkpoint_mgr.clear_all_checkpoints()
            print(f"  🗑️ Cleared {cleared} checkpoints")

        if args.all:
            talents = ["video", "storymaker", "vooks", "adventure_book"]
            if args.package:
                talents.append("thirdparty")
        else:
            talents = args.talent

        results = cmd_run_tests(adb, config, talents, args.package, args.resume, dm)

        # Exit code based on results
        if results and all(r.passed for r in results):
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
