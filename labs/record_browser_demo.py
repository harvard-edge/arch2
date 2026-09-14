#!/usr/bin/env python3
"""
Architecture 2.0: Automated Browser Demo Video Generator
========================================================
Uses Playwright to launch a headless browser, navigate the Quarto Workbench
web companion, smoothly scroll through key exhibits, and inject professional,
animated workshop callout annotations directly onto the screen.

Exports:
  - www/videos/workbench_browser_demo.webm
  - www/videos/workbench_browser_demo.mp4 (via ffmpeg)
"""

import os
from pathlib import Path
import shutil
import subprocess
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEOS_DIR = ROOT / "www" / "videos"
RAW_DIR = VIDEOS_DIR / "browser_raw"
PAGE_URL = f"file://{ROOT}/www/_site/workbench.html"

# Annotation script to inject floating workshop callout cards
INJECT_CSS_JS = """
(() => {
    const style = document.createElement('style');
    style.id = 'workshop-callout-style';
    style.innerHTML = `
        .workshop-overlay {
            position: fixed;
            bottom: 30px;
            right: 30px;
            max-width: 540px;
            padding: 16px 20px;
            background: rgba(15, 23, 42, 0.94);
            backdrop-filter: blur(12px);
            color: #ffffff;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            z-index: 999999;
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            transform: translateY(0);
            opacity: 1;
        }
        .workshop-overlay.hidden {
            transform: translateY(20px);
            opacity: 0;
            pointer-events: none;
        }
        .workshop-tag {
            display: inline-block;
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 3px 8px;
            border-radius: 4px;
            margin-bottom: 6px;
        }
        .tag-teal { background: #0f766e; color: #ccfbf1; }
        .tag-amber { background: #b45309; color: #fef3c7; }
        .tag-purple { background: #6d28d9; color: #ede9fe; }
        .tag-green { background: #15803d; color: #dcfce7; }
        .workshop-title {
            font-size: 16px;
            font-weight: 700;
            margin: 0 0 6px 0;
            color: #f8fafc;
        }
        .workshop-desc {
            font-size: 13px;
            color: #cbd5e1;
            line-height: 1.45;
            margin: 0;
        }
    `;
    document.head.appendChild(style);

    const overlay = document.createElement('div');
    overlay.id = 'workshop-callout';
    overlay.className = 'workshop-overlay hidden';
    overlay.innerHTML = `
        <span id="ws-tag" class="workshop-tag tag-teal">Architecture 2.0</span>
        <h4 id="ws-title" class="workshop-title">Workbench Title</h4>
        <p id="ws-desc" class="workshop-desc">Workbench Description</p>
    `;
    document.body.appendChild(overlay);

    window.showCallout = (tag, tagClass, title, desc) => {
        const ov = document.getElementById('workshop-callout');
        const tg = document.getElementById('ws-tag');
        const tt = document.getElementById('ws-title');
        const ds = document.getElementById('ws-desc');
        tg.textContent = tag;
        tg.className = `workshop-tag ${tagClass}`;
        tt.textContent = title;
        ds.textContent = desc;
        ov.classList.remove('hidden');
    };

    window.hideCallout = () => {
        document.getElementById('workshop-callout').classList.add('hidden');
    };
})();
"""


def record_demo():
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Launching Playwright to record workshop demo from {PAGE_URL}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": 1400, "height": 900},
        )
        page = context.new_page()

        # Step 1: Open the Grounded Workbench Web Page
        page.goto(PAGE_URL)
        page.wait_for_load_state("networkidle")
        page.evaluate(INJECT_CSS_JS)
        time.sleep(1.0)

        # Scene 1: Introduction & The Two-Tier Vision
        page.evaluate(
            """window.showCallout(
                'WORKSHOP OVERVIEW', 'tag-teal',
                'Architecture 2.0: Grounded Micro-Loops Testbed',
                'A live, reproducible experimental testbed demonstrating the boundary between single-layer heuristic plateau and cross-layer AI-Native co-adaptation.'
            )"""
        )
        time.sleep(3.5)

        # Scene 2: Stat Cards & Grounding
        page.mouse.wheel(0, 320)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'CORE RESULTS', 'tag-green',
                '100% vs. 0% Physical Signoff Rate',
                'Across 4 micro-loops, AI-Assisted and AI-Driven optimization fail 100% of physical signoff checks. Only AI-Native cross-layer co-adaptation passes all constraints.'
            )"""
        )
        time.sleep(3.5)

        # Scene 3: The Grand Demonstration Matrix
        page.mouse.wheel(0, 380)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'THE MATRIX', 'tag-purple',
                'The Grand Demonstration Matrix',
                'Four micro-loops evaluated across 3 paradigms: Microarchitecture (Memory Wall), RTL Synthesis (500 MHz Timing), Floorplanning (Routing DRCs), and HW/SW Co-Design.'
            )"""
        )
        time.sleep(4.0)

        # Scene 4: Anti-Reward-Hacking Guarantees
        page.mouse.wheel(0, 420)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'ANTI-REWARD-HACKING', 'tag-amber',
                'No Synthetic Shortcuts or Metric Gaming',
                'Guaranteed by Goodhart\\'s Law defenses: joint compute-memory rooflines, 1,000-vector formal equivalence checks, 2D RUDY track saturation, and disassembly spill profiling.'
            )"""
        )
        time.sleep(4.0)

        # Scene 5: Exhibit A - Systolic Array & The Memory Wall
        page.mouse.wheel(0, 600)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'MICRO-LOOP A', 'tag-teal',
                'Microarchitecture: Breaking the Memory Wall',
                'Single-layer parameter sweeps hit a hard DRAM ceiling (110k cycles). The AI-Native engine pivots dataflow to Weight Stationary, cutting off-chip traffic by 2.73x.'
            )"""
        )
        time.sleep(4.5)

        # Scene 6: Exhibit B - RTL Timing Closure at 500 MHz
        page.mouse.wheel(0, 750)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'MICRO-LOOP B', 'tag-green',
                'RTL Timing: Carry-Save Redundant Arithmetic',
                'Boolean synthesis cannot break 32-stage carry loops (-600 ps WNS). AI-Native refactoring to Carry-Save collapses logic depth to 1 stage (+1.45 ns slack) with formal proof.'
            )"""
        )
        time.sleep(4.5)

        # Scene 7: Exhibit C - Physical Floorplanning & Routing
        page.mouse.wheel(0, 750)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'MICRO-LOOP C', 'tag-purple',
                'Physical Design: Eliminating Routing DRC Shorts',
                'HPWL wirelength minimization packs macros inward, causing 91.8% track saturation and 12 DRC shorts. Rotating pins outward drops congestion to 34.3% (0 DRCs).'
            )"""
        )
        time.sleep(4.5)

        # Scene 8: Exhibit D - HW/SW Co-Design
        page.mouse.wheel(0, 750)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'MICRO-LOOP D', 'tag-amber',
                'HW/SW Co-Design: Register Pressure Collapse',
                'Compiler unrolling thrashes the 32 scalar registers with 32,000 spill cycles. AI-Native co-designs SIMD-4 + post-increment addressing to achieve a 5.1x speedup.'
            )"""
        )
        time.sleep(4.5)

        # Concluding Card
        page.mouse.wheel(0, 500)
        time.sleep(0.8)
        page.evaluate(
            """window.showCallout(
                'TAKEAWAY', 'tag-teal',
                'Silicon Cannot Be Negotiated With',
                'All 4 loops run reproducible in Docker (`./arch2 docker demo`) or in Google Colab with open-source EDA tools (Yosys, Icarus, GCC, SCALE-Sim).'
            )"""
        )
        time.sleep(3.5)

        page.close()
        context.close()
        browser.close()

    # Find the generated video in RAW_DIR
    raw_videos = list(RAW_DIR.glob("*.webm"))
    if not raw_videos:
        print("Error: No raw video captured by Playwright.")
        return

    raw_video = raw_videos[0]
    out_webm = VIDEOS_DIR / "workbench_browser_demo.webm"
    out_mp4 = VIDEOS_DIR / "workbench_browser_demo.mp4"

    shutil.copy2(raw_video, out_webm)
    print(f"Captured Playwright WebM demo: {out_webm}")

    ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    if os.path.exists(ffmpeg_bin):
        print(f"Converting WebM to high-quality MP4 using {ffmpeg_bin}...")
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(out_webm),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            str(out_mp4),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_mp4.exists():
            print(f"Successfully rendered workshop MP4 demo: {out_mp4}")
        else:
            print(f"FFmpeg conversion warning: {res.stderr}")

    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)


if __name__ == "__main__":
    record_demo()
