"""
Regression tests for BaseProvider.get_path().

These specifically cover the folder-sanitization bug where only *leading*
slashes were stripped, allowing a folder value containing ".." components
(e.g. "../../etc/cron.d") to resolve outside DOWNLOAD_DIR.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from providers.base import BaseProvider  # noqa: E402


class _DummyProvider(BaseProvider):
    id = "dummy"
    name = "Dummy"

    def download(self, payload):
        yield {"line": "done", "progress": 100}


@pytest.fixture
def provider(tmp_path, monkeypatch):
    monkeypatch.setenv("DOWNLOAD_DIR", str(tmp_path))
    return _DummyProvider()


def test_get_path_defaults_to_download_dir(provider, tmp_path):
    assert provider.get_path() == str(tmp_path)


def test_get_path_accepts_plain_subfolder(provider, tmp_path):
    path = provider.get_path("MySubfolder")
    assert path == os.path.join(str(tmp_path), "MySubfolder")
    assert os.path.isdir(path)


def test_get_path_strips_leading_slash(provider, tmp_path):
    path = provider.get_path("/MySubfolder")
    assert path == os.path.join(str(tmp_path), "MySubfolder")


@pytest.mark.parametrize(
    "malicious_folder",
    [
        "../../etc/cron.d",
        "../secrets",
        "foo/../../../bar",
    ],
)
def test_get_path_rejects_traversal(provider, malicious_folder):
    with pytest.raises(ValueError):
        provider.get_path(malicious_folder)


def test_get_path_uses_default_subfolder_when_none_given(tmp_path, monkeypatch):
    monkeypatch.setenv("DOWNLOAD_DIR", str(tmp_path))

    class _WithDefault(_DummyProvider):
        default_subfolder = "KHInsider"

    path = _WithDefault().get_path()
    assert path == os.path.join(str(tmp_path), "KHInsider")
