#!/bin/bash
for f in synthesis/book/chapters/*/index.qmd; do
  echo "Checking $f..."
  agy -p "Review $f for formatting errors, unclosed callouts, back-to-back callouts, broken markdown links, inconsistent heading levels, and explicitly patterned LLM Q&A styles ('How do we...'). Output a concise list of issues found." > "${f}_report.txt" &
done
wait
echo "All checks completed."
