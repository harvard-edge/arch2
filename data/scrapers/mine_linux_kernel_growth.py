#!/usr/bin/env python3
"""
Linux Kernel & LLVM Compilation Growth Scraper
==============================================
"""

import os
import csv
import urllib.request
import re
from datetime import datetime
import time
import ssl


def scrape_kernel_org():
    print("Scraping kernel.org for historical release sizes...")
    url = "https://mirrors.edge.kernel.org/pub/linux/kernel/"

    major_versions = ["v2.6", "v3.x", "v4.x", "v5.x", "v6.x"]
    results = []

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for mv in major_versions:
        try:
            req = urllib.request.Request(
                f"{url}{mv}/", headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, context=ctx) as response:
                html = response.read().decode("utf-8")

                pattern = r'<a href="linux-([0-9\.]+)\.tar\.xz">.*?</a>\s+([0-9]{2}-[a-zA-Z]{3}-[0-9]{4})\s+[0-9:]+\s+([0-9]+[MK])'
                matches = re.findall(pattern, html)

                for version, date_str, size_str in matches:
                    date_obj = datetime.strptime(date_str, "%d-%b-%Y")
                    year = date_obj.year

                    size = float(size_str[:-1])
                    if size_str.endswith("K"):
                        size = size / 1024.0

                    results.append(
                        {
                            "version": version,
                            "release_date": date_str,
                            "release_year": year,
                            "tar_xz_size_mb": round(size, 2),
                        }
                    )
            time.sleep(1)
        except Exception as e:
            print(f"Error scraping {mv}: {e}")

    results.sort(key=lambda x: datetime.strptime(x["release_date"], "%d-%b-%Y"))

    os.makedirs("data/source-receipts", exist_ok=True)
    out_file = "data/source-receipts/linux_kernel_growth_historical.csv"

    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["version", "release_date", "release_year", "tar_xz_size_mb"]
        )
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved {len(results)} kernel releases to {out_file}")


if __name__ == "__main__":
    scrape_kernel_org()
