import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class MetadataTests(unittest.TestCase):
    def test_root_project_is_python_311_only(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["requires-python"], ">=3.11")
        self.assertEqual(pyproject["tool"]["poetry"]["dependencies"]["python"], ">=3.11")

    def test_package_project_is_python_311_only(self):
        pyproject = tomllib.loads((ROOT / "flet_stt" / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["requires-python"], ">=3.11")
        self.assertIn("Programming Language :: Python :: 3.11", pyproject["project"]["classifiers"])

    def test_package_versions_match(self):
        pyproject = tomllib.loads((ROOT / "flet_stt" / "pyproject.toml").read_text(encoding="utf-8"))
        pubspec = (ROOT / "flet_stt" / "src" / "flutter" / "flet_stt" / "pubspec.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn(f"version: {pyproject['project']['version']}", pubspec)

    def test_demo_declares_development_extension_package(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["tool"]["flet"]["dev_packages"]["flet-stt"], "flet_stt")

    def test_flutter_extension_uses_speech_to_text_740_or_newer(self):
        pubspec = (ROOT / "flet_stt" / "src" / "flutter" / "flet_stt" / "pubspec.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("speech_to_text: ^7.4.0", pubspec)
