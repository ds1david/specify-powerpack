from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_standard_installation_uses_versioned_release_assets():
    doc = (ROOT / "docs/INSTALLATION_AND_USAGE.md").read_text(encoding="utf-8")
    assert "specify extension add powerpack --from" in doc
    assert "releases/download/v0.4.0/specify-powerpack-extension-v0.4.0.zip" in doc
    assert "specify workflow add powerpack-delivery --from" in doc
    assert "releases/download/v0.4.0/specify-powerpack-workflow-v0.4.0.zip" in doc
    assert "raw.githubusercontent.com/ds1david/specify-powerpack/v0.4.0/catalogs/step-catalog.json" in doc
    assert "--dev" in doc
    assert "For normal consumers, prefer the immutable release installation above." in doc


def test_release_workflow_packages_manifest_at_archive_root():
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "cp -a extensions/powerpack/. dist/extension/" in release
    assert "cp -a workflows/powerpack-delivery/. dist/workflow/" in release
    assert 'zip -qr "../specify-powerpack-extension-${tag}.zip" .' in release
    assert 'zip -qr "../specify-powerpack-workflow-${tag}.zip" .' in release
    assert "SHA256SUMS" in release
