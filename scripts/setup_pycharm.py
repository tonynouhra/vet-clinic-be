#!/usr/bin/env python3
"""
PyCharm setup verification script.
Checks if PyCharm is properly configured for the project.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_pycharm_setup():
    """Check if PyCharm is properly set up."""
    print("🔍 Checking PyCharm Setup...")

    issues = []

    # Check if .idea directory exists
    idea_dir = project_root / ".idea"
    if not idea_dir.exists():
        issues.append("❌ .idea directory not found - project not opened in PyCharm")
    else:
        print("✅ .idea directory found")

    # Check run configurations
    run_configs_dir = idea_dir / "runConfigurations"
    if not run_configs_dir.exists():
        issues.append("❌ Run configurations not found")
    else:
        configs = list(run_configs_dir.glob("*.xml"))
        print(f"✅ Found {len(configs)} run configurations:")
        for config in configs:
            config_name = config.stem.replace("_", " ")
            print(f"   - {config_name}")

    # Check virtual environment
    venv_paths = [
        project_root / "venv" / "bin" / "python",
        project_root / "venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "bin" / "python",
        project_root / ".venv" / "Scripts" / "python.exe",
    ]

    venv_found = False
    for venv_path in venv_paths:
        if venv_path.exists():
            print(f"✅ Virtual environment found: {venv_path}")
            venv_found = True
            break

    if not venv_found:
        issues.append("❌ Virtual environment not found")

    # Check .env file
    env_file = project_root / ".env"
    if not env_file.exists():
        issues.append("❌ .env file not found")
    else:
        print("✅ .env file found")

    # Check configuration
    try:
        from scripts.verify_config import ConfigVerifier

        verifier = ConfigVerifier()
        success, config_issues = verifier.verify_configuration()

        if success:
            print("✅ Configuration verification passed")
        else:
            critical_issues = [
                key
                for key, field_issues in config_issues.items()
                if key in verifier.required_fields
                and verifier.required_fields[key]["critical"]
            ]
            if critical_issues:
                issues.append(
                    f"❌ Critical configuration issues: {', '.join(critical_issues)}"
                )
                print("💡 Run 'python scripts/verify_config.py' for details")
            else:
                print("⚠️  Configuration has warnings (non-critical)")
    except Exception as e:
        issues.append(f"❌ Configuration verification failed: {e}")

    # Check if we can import the app
    try:
        from app.core.config import get_settings

        settings = get_settings()
        print(f"✅ App configuration loaded (Environment: {settings.ENVIRONMENT})")
    except Exception as e:
        issues.append(f"❌ Cannot import app configuration: {e}")

    # Summary
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   {issue}")
        print("\n📖 See docs/PYCHARM_SETUP.md for setup instructions")
        return False
    else:
        print("\n🎉 PyCharm setup looks good!")
        print("\n🚀 You can now:")
        print("   1. Select 'FastAPI Development Server' from run configurations")
        print("   2. Set breakpoints in your code")
        print("   3. Start debugging!")
        return True


def show_quick_start():
    """Show quick start instructions."""
    print("\n📋 Quick Start:")
    print("1. Open PyCharm")
    print("2. File → Open → Select this project directory")
    print("3. Configure Python interpreter:")
    print("   - File → Settings → Project → Python Interpreter")
    print("   - Add Interpreter → Existing Environment")
    print("   - Select: ./venv/bin/python (or ./venv/Scripts/python.exe on Windows)")
    print("4. Fix configuration issues:")
    print("   - Run: python scripts/verify_config.py")
    print("   - Update .env file with required values")
    print("5. Run configurations should appear automatically")
    print("6. Select 'FastAPI Development Server' and click Debug (🐛)")


if __name__ == "__main__":
    print("🔧 PyCharm Setup Verification")
    print("=" * 50)

    if "--help" in sys.argv or "-h" in sys.argv:
        print("PyCharm Setup Verification Script")
        print("\nUsage:")
        print("  python scripts/setup_pycharm.py")
        print("\nThis script checks if PyCharm is properly configured for debugging.")
        sys.exit(0)

    success = check_pycharm_setup()

    if not success:
        show_quick_start()
        sys.exit(1)
    else:
        print("\n📖 For detailed setup instructions, see: docs/PYCHARM_SETUP.md")
        sys.exit(0)
