"""Cumulative student construction course for the Nanochip laboratory.

The course owns persistent student workspaces and ordered lab records. It does
not change the experiment harness or the frozen correctness checks.
"""

from .registry import LABS, LabSpec, get_lab
from .workspace import course_status, init_workspace, load_student_component, record_lab_result
from .api import LabExecutionError, run_lab

__all__ = ["LABS", "LabExecutionError", "LabSpec", "course_status", "get_lab",
           "init_workspace", "load_student_component", "record_lab_result", "run_lab"]
