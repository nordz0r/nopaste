from pathlib import Path


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_version_txt_is_not_a_release_source():
    legacy_version_file = "version" + ".txt"
    searched_files = [
        "pyproject.toml",
        ".github/workflows/release.yml",
        ".github/workflows/dockerhub.yml",
        "Dockerfile",
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
    ]

    for file_path in searched_files:
        p = Path(file_path)
        if p.exists():
            assert legacy_version_file not in p.read_text(encoding="utf-8")


def test_release_image_receives_semantic_release_version():
    release_workflow = read_text(".github/workflows/release.yml")

    assert "APP_VERSION=${{ needs.release.outputs.version }}" in release_workflow
    assert (
        "${{ env.IMAGE_NAME }}:${{ needs.release.outputs.version }}" in release_workflow
    )
    assert (
        "${{ env.GHCR_IMAGE }}:${{ needs.release.outputs.version }}" in release_workflow
    )


def test_dependency_installs_use_frozen_uv_lockfile():
    dockerfile = read_text("Dockerfile")
    ci_workflow = read_text(".github/workflows/ci.yml")

    assert "uv sync --frozen --no-dev" in dockerfile
    assert "uv sync --frozen --extra test --no-install-project" in dockerfile
    assert "uv sync --frozen --extra test --group dev" in ci_workflow
    assert "uv sync --frozen --extra test" in ci_workflow


def test_branch_publish_does_not_overwrite_release_latest_tag():
    dockerhub_workflow = read_text(".github/workflows/dockerhub.yml")

    assert "type=raw,value=latest" not in dockerhub_workflow
    assert "type=ref,event=branch" in dockerhub_workflow
