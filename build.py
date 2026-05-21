"""Automated build+deploy script for flet-stt demo.

Pipeline:
  flet build apk
    -> patch app.zip (replace .pth editable with real .py files)
    -> regenerate app.zip.hash
    -> flutter build apk --release
    -> adb uninstall + install + launch
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
BUILD_FLUTTER = ROOT / "build" / "flutter"
APP_ZIP = BUILD_FLUTTER / "app" / "app.zip"
APP_ZIP_HASH = BUILD_FLUTTER / "app" / "app.zip.hash"
PACKAGE_SRC = ROOT / "flet_stt" / "src" / "flet_stt"
PACKAGE_ID = "com.flet.flet_stt_demo"

SITE_PKG_PREFIX = ".venv/Lib/site-packages/flet_stt/"
FLUTTER_BIN_ENV = "FLUTTER_BIN"


def run(cmd, cwd=None, env=None):
    """Run a command, stream output, and raise on failure."""
    print(f"\n>>> {cmd if isinstance(cmd, str) else ' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, shell=isinstance(cmd, str))
    if result.returncode != 0:
        print(f"FAILED with exit code {result.returncode}")
        sys.exit(1)


def flutter_executable_name():
    return "flutter.bat" if os.name == "nt" else "flutter"


def flutter_from_generated_project():
    """Return the Flutter SDK selected by Flet build, if the generated app has one."""
    local_properties = BUILD_FLUTTER / "android" / "local.properties"
    if not local_properties.exists():
        return None

    for line in local_properties.read_text(encoding="utf-8").splitlines():
        if not line.startswith("flutter.sdk="):
            continue
        flutter_sdk = Path(line.split("=", 1)[1].strip())
        flutter_bin = flutter_sdk / "bin" / flutter_executable_name()
        if flutter_bin.exists():
            return str(flutter_bin)
        print(f"  WARNING: generated Flutter SDK not found at {flutter_bin}")
        return None
    return None


def flutter_cmd():
    """Resolve Flutter without pinning this repo to one local SDK."""
    if os.environ.get(FLUTTER_BIN_ENV):
        return [os.environ[FLUTTER_BIN_ENV]]

    generated_flutter = flutter_from_generated_project()
    if generated_flutter:
        return [generated_flutter]

    path_flutter = shutil.which("flutter")
    if path_flutter:
        return [path_flutter]

    print(
        "ERROR: Flutter executable not found. Run flet build first, put flutter "
        f"on PATH, or set {FLUTTER_BIN_ENV}."
    )
    sys.exit(1)


def step_flet_build():
    """Step 1: run flet build apk.

    Temporarily removes flet-stt from pyproject.toml so serious_python
    doesn't try to pip-install it (it's not on PyPI). The Python files
    are injected later in step 2.
    """
    print("\n=== Step 1: flet build apk ===")
    pyproject = ROOT / "pyproject.toml"
    original = pyproject.read_text(encoding="utf-8")

    # Strip flet-stt from [tool.poetry.dependencies]
    stripped = re.sub(r'\nflet-stt\s*=\s*\{[^}]+\}\n', '\n', original)
    pyproject.write_text(stripped, encoding="utf-8")
    print("  temporarily removed flet-stt from pyproject.toml")

    try:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        run("flet build apk -v", cwd=str(ROOT), env=env)
    finally:
        pyproject.write_text(original, encoding="utf-8")
        print("  restored pyproject.toml")


def step_patch_app_zip():
    """Step 2: patch app.zip and site-packages.

    - Replace main.py in app.zip with the project's main.py
    - Remove stale editable-install artifacts from app.zip
    - Inject flet_stt Python files into build/site-packages/{abi}/ so they
      get bundled into libpythonsitepackages.so during the Gradle build
    """
    print("\n=== Step 2: patch app.zip + site-packages ===")
    if not APP_ZIP.exists():
        print(f"ERROR: {APP_ZIP} not found. Run flet build first.")
        sys.exit(1)

    py_files = list(PACKAGE_SRC.glob("*.py"))
    print(f"  found {len(py_files)} .py files in {PACKAGE_SRC}")

    # --- Patch app.zip: replace main.py, strip stale flet_stt artifacts ---
    tmp_zip = APP_ZIP.with_suffix(".tmp")
    with zipfile.ZipFile(APP_ZIP, "r") as zin, zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if "__editable__" in item.filename and "flet_stt" in item.filename:
                print(f"  removing: {item.filename}")
                continue
            if "flet_stt-" in item.filename and "dist-info" in item.filename:
                if "demo" not in item.filename:
                    print(f"  removing: {item.filename}")
                    continue
            if item.filename.startswith(SITE_PKG_PREFIX):
                print(f"  removing: {item.filename}")
                continue
            if item.filename == "main.py":
                print(f"  replacing: main.py")
                continue
            zout.writestr(item, zin.read(item.filename))

        main_py = ROOT / "main.py"
        if main_py.exists():
            print(f"  adding: main.py (from project root)")
            zout.write(main_py, "main.py")

    tmp_zip.replace(APP_ZIP)
    print("  app.zip patched")

    # --- Inject flet_stt into site-packages for each ABI ---
    site_packages = ROOT / "build" / "site-packages"
    if not site_packages.exists():
        print("  WARNING: build/site-packages not found, skipping injection")
        return

    for abi_dir in site_packages.iterdir():
        if not abi_dir.is_dir():
            continue
        pkg_dir = abi_dir / "flet_stt"
        pkg_dir.mkdir(exist_ok=True)
        for py_file in py_files:
            shutil.copy2(py_file, pkg_dir / py_file.name)
        print(f"  injected flet_stt into site-packages/{abi_dir.name}/")


def step_update_hash():
    """Step 3: regenerate app.zip.hash."""
    print("\n=== Step 3: regenerate app.zip.hash ===")
    sha256 = hashlib.sha256(APP_ZIP.read_bytes()).hexdigest()
    APP_ZIP_HASH.write_text(sha256)
    print(f"  hash: {sha256}")


def step_inject_dart_extension():
    """Step 3b: add flet_stt Dart extension to build's pubspec.yaml and main.dart."""
    print("\n=== Step 3b: inject flet_stt Dart extension ===")

    # Copy Dart source
    dart_src = ROOT / "flet_stt" / "src" / "flutter" / "flet_stt"
    dart_dest = BUILD_FLUTTER / "packages" / "flet_stt"
    if dart_dest.exists():
        shutil.rmtree(dart_dest)
    shutil.copytree(dart_src, dart_dest)
    print(f"  copied Dart extension to {dart_dest}")

    # Patch pubspec.yaml - add or normalize flet_stt dependency
    pubspec = BUILD_FLUTTER / "pubspec.yaml"
    pubspec_text = pubspec.read_text(encoding="utf-8")

    extension_dependency = "  flet_stt:\n    path: packages/flet_stt"
    if re.search(r"(?m)^  flet_stt:\r?\n    path: .*(?:\r?\n)?", pubspec_text):
        pubspec_text, count = re.subn(
            r"(?m)^  flet_stt:\r?\n    path: .*(?:\r?\n)?",
            extension_dependency + "\n",
            pubspec_text,
            count=1,
        )
        if count:
            pubspec.write_text(pubspec_text, encoding="utf-8")
            print("  normalized flet_stt dependency in pubspec.yaml")
    else:
        pubspec_text, count = re.subn(
            r"(  serious_python:\s+\S+)",
            r"\1\n  flet_stt:\n    path: packages/flet_stt",
            pubspec_text,
            count=1,
        )
        if count == 0:
            print("  ERROR: could not find serious_python dependency in pubspec.yaml")
            sys.exit(1)
        pubspec.write_text(pubspec_text, encoding="utf-8")
        print("  added flet_stt dependency to pubspec.yaml")
    run([*flutter_cmd(), "pub", "get"], cwd=str(BUILD_FLUTTER))

    # Patch main.dart - import and register extension
    main_dart = BUILD_FLUTTER / "lib" / "main.dart"
    main_text = main_dart.read_text(encoding="utf-8")
    if "package:flet_stt" not in main_text:
        main_text, count = re.subn(
            r'(import\s+"python\.dart";)',
            r"\1\nimport 'package:flet_stt/flet_stt.dart' as flet_stt;",
            main_text,
            count=1,
        )
        if count == 0:
            print('  ERROR: could not find \'import "python.dart";\' in main.dart')
            sys.exit(1)
        main_text, count = re.subn(
            r'(List<FletExtension>\s+extensions\s*=\s*\[)\s*\]',
            r'\1\n  flet_stt.Extension(),\n]',
            main_text,
            count=1,
        )
        if count == 0:
            print("  ERROR: could not find extensions list in main.dart")
            sys.exit(1)
        main_dart.write_text(main_text, encoding="utf-8")
        print("  registered flet_stt extension in main.dart")


def step_flutter_build():
    """Step 4: flutter build apk --release."""
    print("\n=== Step 4: flutter build apk --release ===")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    # Point to site-packages if it exists (older flet versions create it)
    site_packages = ROOT / "build" / "site-packages"
    if site_packages.exists():
        env["SERIOUS_PYTHON_SITE_PACKAGES"] = str(site_packages)
        print(f"  SERIOUS_PYTHON_SITE_PACKAGES={site_packages}")

    run([*flutter_cmd(), "build", "apk", "--release"], cwd=str(BUILD_FLUTTER), env=env)


def step_install():
    """Step 5: adb uninstall + install + launch."""
    print("\n=== Step 5: install on device ===")
    apk = BUILD_FLUTTER / "build" / "app" / "outputs" / "flutter-apk" / "app-release.apk"
    if not apk.exists():
        print(f"ERROR: APK not found at {apk}")
        sys.exit(1)

    subprocess.run(["adb", "uninstall", PACKAGE_ID], capture_output=True)
    print(f"  uninstalled {PACKAGE_ID} (if present)")

    run(["adb", "install", str(apk)])
    print("  installed successfully")

    run(["adb", "shell", "monkey", "-p", PACKAGE_ID, "-c", "android.intent.category.LAUNCHER", "1"])
    print("  launched app")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build and deploy flet-stt demo")
    parser.add_argument("--skip-flet", action="store_true", help="skip flet build apk (reuse existing build dir)")
    parser.add_argument("--skip-install", action="store_true", help="skip adb install + launch")
    args = parser.parse_args()

    if not args.skip_flet:
        step_flet_build()

    step_patch_app_zip()
    step_update_hash()
    step_inject_dart_extension()
    step_flutter_build()

    if not args.skip_install:
        step_install()

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
