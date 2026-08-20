#!/usr/bin/env bash
# Assemble the full Architecture 2.0 site into ./_site
#
#   _site/         <- landing page (www/)
#   _site/about.html
#   _site/tools/   <- tool registry (tools/)
#   _site/book/    <- the book (book/, rendered via the arch2 CLI)
#
# Each sub-project renders into its own local _site/ (see each _quarto.yml) and
# is copied into the top-level _site/, so the projects never clobber one another.
#
# Usage:
#   .github/scripts/build_site.sh              # full build, including the book
#   SKIP_BOOK=1 .github/scripts/build_site.sh  # skip the heavy book render
set -euo pipefail
cd "$(dirname "$0")/../.."

rm -rf _site
mkdir -p \
  _site/book \
  _site/design-loop-card \
  _site/examples/design-loop-cards \
  _site/images \
  _site/schemas \
  _site/tools

echo "==> Copying shared site assets"
cp book/images/favicon.svg _site/images/
cp book/images/favicon-16.png _site/images/
cp book/images/favicon-32.png _site/images/
cp book/images/favicon-48.png _site/images/
cp book/images/favicon.ico _site/images/
cp book/images/apple-touch-icon.png _site/images/
cp book/images/icon-192.png _site/images/
cp book/images/icon-512.png _site/images/
cp book/images/arch2-card.png _site/images/
cp book/images/site.webmanifest _site/images/

echo "==> Copying public design-loop card artifacts"
cp -R schemas/. _site/schemas/
cp -R design-loop-card/. _site/design-loop-card/
cp -R examples/design-loop-cards/. _site/examples/design-loop-cards/

echo "==> Building generated registry indexes"
PYTHONPATH=.github/scripts python3 .github/scripts/build_catalog_index.py
PYTHONPATH=.github/scripts python3 .github/scripts/build_workshops_index.py
PYTHONPATH=.github/scripts python3 .github/scripts/build_readings_index.py
python3 .github/scripts/render_book_navbar.py

if [[ "${SKIP_BOOK:-0}" != "1" ]]; then
  echo "==> Rendering book (arch2 CLI)"
  # Pages publishing should verify that the site and downloadable artifacts build.
  # Manuscript PDF layout audits are run as a separate book-quality gate. The
  # render still enforces generated-asset cleanliness so a release cannot publish
  # figures that disagree with their tracked sources. A local uncommitted review
  # may opt out explicitly with ARCH2_SKIP_ASSET_DRIFT=1.
  ./arch2 render --no-layout
  cp -r book/_build/* _site/book/
else
  echo "==> Skipping book render (SKIP_BOOK=1)"
  if [[ -d book/_build ]] && compgen -G "book/_build/*" > /dev/null; then
    echo "==> Using existing book/_build artifacts"
    cp -r book/_build/* _site/book/
  else
    echo "warning: book/_build is empty; _site/book will not be populated" >&2
  fi
fi

echo "==> Rendering tool registry"
quarto render tools
cp -r tools/_site/* _site/tools/

echo "==> Rendering landing + about"
# Measure the manuscript at build time and pass the numbers in as metadata, so
# the landing page reports exact figures without a runtime request. A failure
# here must not break the site: the strip degrades to empty values.
stat_args=()
if stats_output="$(python3 .github/scripts/manuscript_stats.py 2>/dev/null)"; then
  while IFS= read -r stat_line; do
    [[ -n "$stat_line" ]] && stat_args+=("-M" "$stat_line")
  done <<< "$stats_output"
else
  echo "warning: manuscript stats unavailable; landing strip will be empty" >&2
fi
quarto render www ${stat_args[@]+"${stat_args[@]}"}
cp -r www/_site/* _site/

echo "==> Rewriting assembled-site links"
if [[ -d _site/tools ]]; then
  find _site/tools -name '*.html' -print0 | xargs -0 perl -0pi -e '
    s#href="\./book/#href="../book/#g;
    s#href="\./about\.html"#href="../about.html"#g;
    s#href="\./start\.html"#href="../start.html"#g;
    s#href="\./readings\.html"#href="../readings.html"#g;
    s#href="\./workshops\.html"#href="../workshops.html"#g;
    s#href="\./submit\.html"#href="../submit.html"#g;
    s#href="\./submit-resource\.html"#href="../submit-resource.html"#g;
    s#href="\./submit-workshop\.html"#href="../submit-workshop.html"#g;
    s#href="\./tools/index\.html"#href="./index.html"#g;
    s#href="\./images/#href="../images/#g;
    s#class="navbar-brand" href="\./index\.html"#class="navbar-brand" href="../index.html"#g;
  '

  if grep -R -n -E \
    'href="\./(about|start|readings|workshops|submit|submit-resource|submit-workshop)\.html"' \
    _site/tools; then
    echo "error: assembled tool pages retain root-relative navigation links" >&2
    exit 1
  fi
fi

python3 .github/scripts/check_site_accessibility.py \
  _site/*.html _site/tools/*.html
python3 .github/scripts/check_site_links.py _site

echo "==> Site assembled in ./_site"
find _site -maxdepth 2 -name '*.html' | sort
