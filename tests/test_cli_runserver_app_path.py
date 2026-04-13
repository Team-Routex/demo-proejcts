import unittest

from raft.cli.main import _normalize_app_path


class CliRunserverAppPathTests(unittest.TestCase):
    def test_bare_module_is_normalized(self) -> None:
        self.assertEqual(_normalize_app_path("app"), "app:app")
        self.assertEqual(_normalize_app_path("main"), "main:app")

    def test_explicit_attribute_is_preserved(self) -> None:
        self.assertEqual(_normalize_app_path("app:application"), "app:application")
        self.assertEqual(_normalize_app_path("pkg.module:app"), "pkg.module:app")

    def test_empty_or_whitespace_falls_back_to_default(self) -> None:
        self.assertEqual(_normalize_app_path(""), "app:app")
        self.assertEqual(_normalize_app_path("   "), "app:app")


if __name__ == "__main__":
    unittest.main()
