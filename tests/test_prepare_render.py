from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PREPARE_RENDER_PATH = ROOT / "book" / "scripts" / "prepare_render.py"
SPEC = importlib.util.spec_from_file_location("prepare_render", PREPARE_RENDER_PATH)
assert SPEC and SPEC.loader
prepare_render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare_render)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def figure_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    run_git(tmp_path, "init", "--initial-branch=main")
    run_git(tmp_path, "config", "user.name", "Figure Test")
    run_git(tmp_path, "config", "user.email", "figure@example.com")

    source = tmp_path / "figure.svg"
    target = tmp_path / "figure.pdf"
    source.write_text("svg-v1\n", encoding="utf-8")
    target.write_text("pdf-v1\n", encoding="utf-8")
    run_git(tmp_path, "add", source.name, target.name)
    run_git(tmp_path, "commit", "-m", "add synchronized figure")
    return tmp_path, source, target


def test_clean_checkout_mtimes_do_not_make_figure_stale(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    target_time = target.stat().st_mtime
    os.utime(source, (target_time + 60, target_time + 60))

    assert not prepare_render.is_stale(source, target, repo_root=repo)


def test_newer_committed_source_makes_figure_stale(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    source.write_text("svg-v2\n", encoding="utf-8")
    run_git(repo, "add", source.name)
    run_git(repo, "commit", "-m", "revise source only")
    source_time = source.stat().st_mtime
    os.utime(target, (source_time + 60, source_time + 60))

    assert prepare_render.is_stale(source, target, repo_root=repo)


def test_later_committed_target_synchronizes_figure(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    source.write_text("svg-v2\n", encoding="utf-8")
    run_git(repo, "add", source.name)
    run_git(repo, "commit", "-m", "revise source")
    target.write_text("pdf-v2\n", encoding="utf-8")
    run_git(repo, "add", target.name)
    run_git(repo, "commit", "-m", "refresh target")

    assert not prepare_render.is_stale(source, target, repo_root=repo)


def test_dirty_source_with_clean_target_is_stale(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    source.write_text("svg-working-copy\n", encoding="utf-8")
    target_time = target.stat().st_mtime
    os.utime(source, (target_time - 60, target_time - 60))

    assert prepare_render.is_stale(source, target, repo_root=repo)


def test_dirty_target_is_not_regenerated_again(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    target.write_text("pdf-working-copy\n", encoding="utf-8")
    target_time = target.stat().st_mtime
    os.utime(source, (target_time + 60, target_time + 60))

    assert not prepare_render.is_stale(source, target, repo_root=repo)


def test_missing_target_is_stale(tmp_path: Path) -> None:
    source = tmp_path / "figure.svg"
    source.write_text("svg-v1\n", encoding="utf-8")

    assert prepare_render.is_stale(source, tmp_path / "figure.pdf", repo_root=tmp_path)


def test_untracked_source_with_clean_target_is_stale(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    run_git(repo, "rm", "--cached", source.name)

    assert prepare_render.is_stale(source, target, repo_root=repo)


def test_untracked_target_for_clean_source_is_stale(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    run_git(repo, "rm", "--cached", target.name)

    assert prepare_render.is_stale(source, target, repo_root=repo)


def test_non_git_directory_falls_back_to_mtime(tmp_path: Path) -> None:
    source = tmp_path / "figure.svg"
    target = tmp_path / "figure.pdf"
    source.write_text("svg-v1\n", encoding="utf-8")
    target.write_text("pdf-v1\n", encoding="utf-8")
    target_time = target.stat().st_mtime
    os.utime(source, (target_time + 60, target_time + 60))

    assert prepare_render.is_stale(source, target, repo_root=tmp_path)


def test_prune_keeps_tracked_unreferenced_sources(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, source, target = figure_repo
    kept = prepare_render.prune_unreferenced_derivatives(repo, [], repo_root=repo)
    assert source.exists() and target.exists()
    assert set(kept) == {source, target}


def test_prune_removes_only_untracked_derivative(
    figure_repo: tuple[Path, Path, Path],
) -> None:
    repo, _, _ = figure_repo
    svg = repo / "draft.svg"
    pdf = repo / "draft.pdf"
    orphan_pdf = repo / "orphan.pdf"
    svg.write_text("svg\n", encoding="utf-8")
    pdf.write_text("pdf\n", encoding="utf-8")
    orphan_pdf.write_text("pdf\n", encoding="utf-8")
    prepare_render.prune_unreferenced_derivatives(repo, ["figure"], repo_root=repo)
    assert svg.exists(), "an untracked SVG is authored source and must survive"
    assert not pdf.exists(), "an untracked PDF with its SVG twin is regenerable"
    assert orphan_pdf.exists(), "a PDF without an SVG twin may be authored art"


def test_prune_keeps_referenced_files(figure_repo: tuple[Path, Path, Path]) -> None:
    repo, source, target = figure_repo
    kept = prepare_render.prune_unreferenced_derivatives(
        repo, ["figure"], repo_root=repo
    )
    assert kept == [] and source.exists() and target.exists()
