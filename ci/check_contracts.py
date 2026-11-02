"""Unit checks of the contract selector itself; does not alter default pytest."""
import unittest
import pytest
from test_targets import classify
class SelectionTests(unittest.TestCase):
 def test_shared(self):self.assertEqual(classify('tests/test_core.py::Release::test_01_unique_and_counts'),'shared')
 def test_development(self):self.assertEqual(classify('tests/test_deployment_info.py::test_missing_git'),'development')
 def test_production(self):self.assertEqual(classify('tests/test_ui.py::Interface::test_01_home_and_presets'),'production')
 def test_unknown_fails_closed(self):
  with self.assertRaises(pytest.UsageError):classify('tests/test_new_unknown.py::test_something')
if __name__=='__main__':unittest.main()
