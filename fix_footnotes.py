import re


def fix_file(path, old_fn, new_fn):
    with open(path, "r") as f:
        text = f.read()

    if old_fn:
        text = text.replace(old_fn, new_fn)

    # Fix the colon
    text = re.sub(r"\*\*(.*?):\*\*", r"**\1**:", text)

    with open(path, "w") as f:
        f.write(text)


fix_file(
    "book/contents/chapters/01-moonshot/01-moonshot.qmd",
    "[^fn-agentic-eda-ci-parallel]",
    "[^fn-agentic-eda-ci-parallel-c01]",
)
fix_file("book/contents/chapters/03-lifecycle/03-lifecycle.qmd", None, None)
fix_file("book/contents/chapters/06-environments/06-environments.qmd", None, None)
fix_file("book/contents/chapters/07-feedback/07-feedback.qmd", None, None)
fix_file("book/contents/chapters/08-loop/08-loop.qmd", None, None)
fix_file("book/contents/chapters/09-patterns/09-patterns.qmd", None, None)
fix_file("book/contents/chapters/11-ownership/11-ownership.qmd", None, None)
fix_file("book/contents/chapters/12-ecosystem/12-ecosystem.qmd", None, None)
