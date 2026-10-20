"""Nanochip (MoonshotAI/nano-kpu) 6-Stage AI-Native Design Loop Workbench CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[1],
        *here.parents,
        Path.cwd().resolve(),
        *Path.cwd().resolve().parents,
    ):
        if (candidate / "CITATION.cff").exists() and (candidate / "book").is_dir():
            return candidate
    return here.parents[1]


ROOT = _find_repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

console = Console()

lab_app = typer.Typer(
    help="Execute and inspect Nanochip 6-Stage AI-Native Design Loop Workbench labs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
docker_app = typer.Typer(
    help="Manage Docker container environment and containerized EDA execution.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
agent_app = typer.Typer(
    help="Autonomous AI-Native design agent operating in closed physical loops.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
referee_app = typer.Typer(
    help="Execute physical verification referees and adversarial red team cheat suite.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# =============================================================================
# Nanochip (MoonshotAI/nano-kpu) 6-Stage AI-Native Design Loop Workbench
# =============================================================================

NANOCHIP_ROOT = ROOT / "nanochip"
LAB_MAPPING = {
    "01": NANOCHIP_ROOT / "labs" / "01-formulate",
    "02": NANOCHIP_ROOT / "labs" / "02-explore",
    "03": NANOCHIP_ROOT / "labs" / "03-implement",
    "04": NANOCHIP_ROOT / "labs" / "04-evaluate",
    "05": NANOCHIP_ROOT / "labs" / "05-interpret",
    "06": NANOCHIP_ROOT / "labs" / "06-commit",
    "1": NANOCHIP_ROOT / "labs" / "01-formulate",
    "2": NANOCHIP_ROOT / "labs" / "02-explore",
    "3": NANOCHIP_ROOT / "labs" / "03-implement",
    "4": NANOCHIP_ROOT / "labs" / "04-evaluate",
    "5": NANOCHIP_ROOT / "labs" / "05-interpret",
    "6": NANOCHIP_ROOT / "labs" / "06-commit",
    "formulate": NANOCHIP_ROOT / "labs" / "01-formulate",
    "explore": NANOCHIP_ROOT / "labs" / "02-explore",
    "implement": NANOCHIP_ROOT / "labs" / "03-implement",
    "evaluate": NANOCHIP_ROOT / "labs" / "04-evaluate",
    "interpret": NANOCHIP_ROOT / "labs" / "05-interpret",
    "commit": NANOCHIP_ROOT / "labs" / "06-commit",
}


@lab_app.command("list")
def lab_list() -> None:
    """List all 6 lifecycle labs in the Nanochip (MoonshotAI/nano-kpu) Workbench."""
    import yaml

    table = Table(
        title="Architecture 2.0 Nanochip Workbench: 6-Stage AI-Native Design Loop Labs",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("ID", style="bold cyan", justify="center")
    table.add_column("Lifecycle Stage", style="bold yellow")
    table.add_column("Title", style="bold white")
    table.add_column("Book Chapters", style="green")
    table.add_column("Target Artifact in nanochip/kpu")

    for lab_id in ("01", "02", "03", "04", "05", "06"):
        lab_dir = LAB_MAPPING[lab_id]
        contract_file = lab_dir / "contract.yaml"
        if contract_file.exists():
            data = yaml.safe_load(contract_file.read_text(encoding="utf-8"))
            title = data.get("title", lab_dir.name)
            stage = data.get("stage", lab_dir.name)
            chapters = ", ".join(str(c) for c in data.get("book_chapters", []))
            target = data.get("target_system", "msh_chip_top")
            table.add_row(lab_id, str(stage), str(title), chapters, str(target))
    console.print(table)


DOCKER_IMAGE = "arch2-workbench:latest"


def _run_in_docker(command: List[str], interactive: bool = False) -> int:
    docker_bin = shutil.which("docker")
    if not docker_bin:
        console.print("[red]Error: 'docker' executable not found on PATH.[/red]")
        return 1
    cmd = [docker_bin, "run", "--rm"]
    if interactive and sys.stdin.isatty():
        cmd.append("-it")
    cmd.extend(["-v", f"{ROOT}:/workspace", DOCKER_IMAGE])
    cmd.extend(command)
    res = subprocess.run(cmd)
    return res.returncode


@docker_app.command("build")
def docker_build(
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Do not use cache when building image"
    ),
) -> None:
    """Build the arch2-workbench Docker container image."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        console.print("[red]Error: 'docker' executable not found on PATH.[/red]")
        raise typer.Exit(1)
    dockerfile = ROOT / "labs" / "docker" / "Dockerfile"
    if not dockerfile.exists():
        console.print(f"[red]Error: Dockerfile not found at {dockerfile}.[/red]")
        raise typer.Exit(1)
    cmd = [docker_bin, "build", "-t", DOCKER_IMAGE, "-f", str(dockerfile), str(ROOT)]
    if no_cache:
        cmd.append("--no-cache")
    console.print(f"[bold cyan]Building Docker image {DOCKER_IMAGE}...[/bold cyan]")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        console.print(f"[green]✔ Successfully built {DOCKER_IMAGE}[/green]")
    raise typer.Exit(res.returncode)


@docker_app.command("run")
def docker_run_cmd(
    command: List[str] = typer.Argument(
        ..., help="Command to run inside the Docker container"
    ),
) -> None:
    """Execute any command inside the arch2-workbench Docker container."""
    code = _run_in_docker(command, interactive=True)
    raise typer.Exit(code)


@docker_app.command("lab")
def docker_lab(
    target: str = typer.Argument("all", help="Target lab: 01..06 or all"),
    mode: str = typer.Option(
        "verify", "--mode", "-m", help="Lab mode: verify, break, or summary"
    ),
) -> None:
    """Run Nanochip Workbench labs inside the Docker container."""
    if target.lower().strip() in ("all", "*"):
        cmd = ["python3", "nanochip/labs/run_all.py", "--mode", mode]
    else:
        lab_dir = LAB_MAPPING.get(target.lower().strip())
        if not lab_dir:
            console.print(f"[red]Unknown lab '{target}'. Choose 01..06 or all.[/red]")
            raise typer.Exit(1)
        cmd = ["python3", f"nanochip/labs/{lab_dir.name}/lab.py", "--mode", mode]
    code = _run_in_docker(cmd)
    raise typer.Exit(code)


@docker_app.command("demo")
def docker_demo() -> None:
    """Run the Nanochip 6-stage loop demonstration inside the Docker container."""
    code = _run_in_docker(
        ["python3", "-m", "nanochip.engine.runner", "--mode", "replay"]
    )
    raise typer.Exit(code)


@lab_app.command("run")
def lab_run(
    target: str = typer.Argument(
        "all",
        help="Target lab: 01 (formulate), 02 (explore), 03 (implement), 04 (evaluate), 05 (interpret), 06 (commit), or all",
    ),
    mode: str = typer.Option(
        "verify",
        "--mode",
        "-m",
        help="Execution mode: 'verify' (default), 'break' (trigger failure/reward-hack), or 'summary'",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON output",
    ),
    use_docker: bool = typer.Option(
        False,
        "--docker",
        help="Execute inside the arch2-workbench Docker container",
    ),
) -> None:
    """Execute one or all 6 lifecycle labs in the Nanochip Workbench."""
    target_clean = target.lower().strip()
    if target_clean in ("all", "*"):
        script = NANOCHIP_ROOT / "labs" / "run_all.py"
        cmd = [sys.executable, str(script), "--mode", mode]
        if as_json:
            cmd.append("--json")
        if use_docker:
            raise typer.Exit(
                _run_in_docker(["python3", "nanochip/labs/run_all.py", "--mode", mode])
            )
        res = subprocess.run(cmd)
        raise typer.Exit(res.returncode)

    if target_clean not in LAB_MAPPING:
        console.print(
            f"[red]Unknown lab identifier '{target}'. Choose from: 01..06 (formulate, explore, implement, evaluate, interpret, commit), or all.[/red]"
        )
        raise typer.Exit(1)

    lab_dir = LAB_MAPPING[target_clean]
    script = lab_dir / "lab.py"
    cmd = [sys.executable, str(script), "--mode", mode]
    if as_json:
        cmd.append("--json")
    if use_docker:
        raise typer.Exit(
            _run_in_docker(
                ["python3", f"nanochip/labs/{lab_dir.name}/lab.py", "--mode", mode]
            )
        )
    res = subprocess.run(cmd)
    raise typer.Exit(res.returncode)


@lab_app.command("demo")
def lab_demo() -> None:
    """Run all 6 Nanochip lifecycle labs and print the campaign summary."""
    script = NANOCHIP_ROOT / "labs" / "run_all.py"
    res = subprocess.run([sys.executable, str(script)])
    raise typer.Exit(res.returncode)


@lab_app.command("cockpit")
def cockpit_cmd(
    port: int = typer.Option(
        8080, "--port", "-p", help="HTTP port for the X-Ray Cockpit server"
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Run self-test of all 5 live Cockpit referee endpoints and exit",
    ),
) -> None:
    """Launch the Architecture 2.0 Nanochip X-Ray Cockpit web server."""
    script = NANOCHIP_ROOT / "cockpit" / "server.py"
    cmd = [sys.executable, str(script), "--port", str(port)]
    if check:
        cmd.append("--check")
    res = subprocess.run(cmd)
    raise typer.Exit(res.returncode)


@lab_app.command("tutorial")
def lab_tutorial(
    live: bool = typer.Option(
        False,
        "--live",
        help="Run live Verilator, Yosys Nangate45 STA, audit.py, and fxmodel.py referees",
    ),
    turn: int = typer.Option(
        -1,
        "--turn",
        "-t",
        help="Inspect a specific turn (0..4), or -1 for the full 5-turn trajectory",
    ),
) -> None:
    """Walk through the 5-turn Kimi K3 nano-kpu co-design trajectory across all 6 stages."""
    from nanochip.engine.runner import NanochipLoopRunner

    runner = NanochipLoopRunner()
    data = runner.run_replay(turn_id=turn if turn >= 0 else None)
    meta = data.get("campaign_meta", {})
    console.print()
    console.print(
        Panel(
            f"[bold white]ARCHITECTURE 2.0 // NANOCHIP 6-STAGE CO-DESIGN TRAJECTORY[/bold white]\n"
            f"[cyan]Target Chip:[/cyan] {meta.get('target_chip', 'msh_chip_top (MoonshotAI/nano-kpu)')}\n"
            f"[cyan]Lifecycle Stages:[/cyan] Formulate ──► Explore ──► Implement ──► Evaluate ──► Interpret ──► Commit\n"
            f"[dim]Integrity Lock: {'OK (35/35 SHA-256 files verified)' if data.get('integrity', {}).get('ok') else 'MODIFIED'}[/dim]",
            box=box.ROUNDED,
            border_style="bright_blue",
        )
    )

    tbl = Table(box=box.ROUNDED, header_style="bold cyan", show_lines=True)
    tbl.add_column("Turn", justify="center", style="bold white", width=6)
    tbl.add_column("Layer", justify="left", style="yellow", width=18)
    tbl.add_column("2. Explore Proposal & Bet", justify="left", width=28)
    tbl.add_column("4. Evaluate Silicon Result", justify="left", width=26)
    tbl.add_column("5. Interpret Return Arrow", justify="left", width=24)

    for t_obj in data.get("turns", []):
        tid = t_obj.get("turn_id")
        exp = t_obj.get("explore", {})
        ev = t_obj.get("evaluate", {})
        interp = t_obj.get("interpret", {})
        arrow = interp.get("return_arrow_target", "")
        arrow_style = (
            "green"
            if "Commit" in arrow
            else "red"
            if "Implement" in arrow
            else "yellow"
            if "Explore" in arrow
            else "magenta"
        )
        tbl.add_row(
            f"T{tid}",
            exp.get("operational_layer", ""),
            f"[bold]{exp.get('title', '')}[/bold]\nBet: {exp.get('predicted_cycles_per_token', 0):,.0f} cyc/tok ({exp.get('predicted_tokens_per_sec', 0):,.1f} tok/s)",
            f"Measured: {ev.get('measured_cycles_per_token', 0):,.1f} cyc/tok\n({ev.get('measured_tokens_per_sec', 0):,.1f} tok/s) | Gates: {'[green]PASS[/green]' if ev.get('all_gates_passed') else '[red]FAIL[/red]'}",
            f"[bold {arrow_style}]──► {arrow}[/bold {arrow_style}]\n[dim]{interp.get('root_cause_category', '')}[/dim]",
        )
    console.print(tbl)

    if live:
        console.print(
            "\n[bold cyan]Running live Verilator + Yosys Nangate45 + fxmodel referees...[/bold cyan]"
        )
        live_res = runner.run_live_verify(quick=True)
        status_str = (
            "[bold green]ALL LIVE REFEREES PASSED[/bold green]"
            if live_res.get("ok")
            else "[bold red]LIVE REFEREE FAILURE[/bold red]"
        )
        console.print(
            Panel(
                f"{status_str} in {live_res.get('wall_seconds')}s\n"
                f"• Turn 1 Audit Cheat Caught: {not live_res['turn1_audit_cheat_caught']['ok']} ({len(live_res['turn1_audit_cheat_caught']['hard'])} hard violations)\n"
                f"• Turn 1 Selfmodel Bit-Mismatch Caught: {not live_res['turn1_selfmodel_drift_caught']['bit_exact']} (cos={live_res['turn1_selfmodel_drift_caught']['row_cosine_min']:.4f})\n"
                f"• Turn 4 msh_deq.v Yosys Nangate45: {live_res['turn4_msh_deq_yosys']['area_um2']:,.1f} um² | {live_res['turn4_msh_deq_yosys']['critical_path_ns']:.3f} ns\n"
                f"• Turn 4 Full-Chip Verilator Quick Sim: {live_res['turn4_kpu_evaluate']['tokens_per_sec']:,.2f} tok/s (cos_min={live_res['turn4_kpu_evaluate']['cos_min']:.4f})",
                title="[bold cyan]Live Hardware & Simulation Verification Receipt[/bold cyan]",
                box=box.ROUNDED,
                border_style="green" if live_res.get("ok") else "red",
            )
        )
    console.print()


@agent_app.command("run")
def agent_run(
    model: str = typer.Option(
        "reference",
        "--model",
        "-m",
        help="Proposer backend: 'reference' (default), 'kimi-k3', 'claude', 'gemini', or 'openai'",
    ),
    live_referees: bool = typer.Option(
        False,
        "--live",
        help="Also run live Verilator and Yosys Nangate45 referees after agent loop",
    ),
) -> None:
    """Run the 6-stage Nanochip closed loop with a pluggable AI proposer."""
    from nanochip.engine.runner import NanochipLoopRunner

    runner = NanochipLoopRunner()
    res = runner.run_agent_loop(proposer_provider=model, live_referees=live_referees)
    pmeta = res.get("proposer", {})
    console.print(
        Panel(
            f"[bold white]Requested Proposer:[/bold white] {pmeta.get('requested_provider')} ({pmeta.get('model_id')})\n"
            f"[bold white]Effective Provider:[/bold white] {pmeta.get('effective_provider')} (API Key Detected: {pmeta.get('api_key_detected')})\n"
            f"[dim]Completed 5-turn closed-loop trajectory in {res.get('wall_seconds')}s[/dim]",
            title="[bold cyan]Nanochip 6-Stage Closed-Loop Agent Run[/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
        )
    )
    for t_obj in res.get("turns", []):
        exp = t_obj.get("explore", {})
        interp = t_obj.get("interpret", {})
        console.print(
            f"[bold]Turn {t_obj.get('turn_id')} ({exp.get('operational_layer')}):[/bold] {exp.get('title')}\n"
            f"  [dim]Hypothesis:[/dim] {exp.get('hypothesis')}\n"
            f"  [dim]5. Interpret Return Arrow:[/dim] [bold yellow]{interp.get('return_arrow_target')}[/bold yellow] — {interp.get('causal_diagnosis')}\n"
        )


@agent_app.command("models")
def agent_models() -> None:
    """List supported AI proposer backends and inspect API key availability."""
    from nanochip.engine.proposers import SUPPORTED_PROPOSERS, resolve_proposer

    tbl = Table(
        title="Nanochip Supported Stage-2 (Explore) AI Proposers", box=box.ROUNDED
    )
    tbl.add_column("Provider", style="bold cyan")
    tbl.add_column("Default Model ID", style="bold white")
    tbl.add_column("API Key Detected", justify="center")
    tbl.add_column("Effective Runtime Mode")
    for p in SUPPORTED_PROPOSERS:
        meta = resolve_proposer(p)
        tbl.add_row(
            meta.provider,
            meta.model_id,
            "[green]yes[/green]"
            if meta.api_key_detected
            else "[yellow]no (uses recorded fallback)[/yellow]",
            meta.effective_provider,
        )
    console.print(tbl)


@agent_app.command("inspect")
def agent_inspect(
    turn: int = typer.Option(
        4, "--turn", "-t", help="Turn ID (0..4) to inspect in detail"
    ),
) -> None:
    """Inspect the 6-stage lifecycle records for a specific turn in nanochip/trajectories/."""
    from nanochip.engine.runner import NanochipLoopRunner

    runner = NanochipLoopRunner()
    t_obj = runner.load_turn(turn).to_dict()
    console.print_json(data=t_obj)


@referee_app.command("check")
def referee_check(
    quick: bool = typer.Option(
        True,
        "--quick/--full",
        help="Run quick 16-token Verilator sim (default) or full 48+16 token + randreset + 2x latency sweep",
    ),
) -> None:
    """Run live Nanochip physical & functional verification referees on msh_chip_top."""
    from nanochip.engine.runner import NanochipLoopRunner

    runner = NanochipLoopRunner()
    res = runner.run_live_verify(quick=quick)
    console.print_json(data=res)
    if not res.get("ok"):
        raise typer.Exit(1)


@referee_app.command("red-team")
def referee_red_team() -> None:
    """Run the adversarial '--mode break' battery across all 6 Nanochip lifecycle stages."""
    script = NANOCHIP_ROOT / "labs" / "run_all.py"
    res = subprocess.run([sys.executable, str(script), "--mode", "break"])
    raise typer.Exit(res.returncode)


@lab_app.command("play")
def lab_play(
    lab_id: str = typer.Argument("01", help="Target lab ID (01..06)"),
) -> None:
    """Run both '--mode break' and '--mode verify' for a target Nanochip lifecycle lab."""
    target_clean = lab_id.lower().strip()
    if target_clean not in LAB_MAPPING:
        console.print(f"[red]Unknown lab '{lab_id}'. Choose 01..06.[/red]")
        raise typer.Exit(1)
    script = LAB_MAPPING[target_clean] / "lab.py"
    subprocess.run([sys.executable, str(script), "--mode", "break"], check=True)
    subprocess.run([sys.executable, str(script), "--mode", "verify"], check=True)


@lab_app.command("experiment")
def lab_experiment() -> None:
    """Evaluate analytical DRAM byte-traffic rooflines across FP32, FP16, and INT4 group-128."""
    from nanochip.engine.roofline import evaluate_rooflines

    console.print_json(data=evaluate_rooflines())
