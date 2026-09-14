# VHS Tape: Architecture 2.0 Grounded Workbench Master Demo
# Target: Workshop Presentation & Screencast

Output "www/videos/workbench_terminal_demo.mp4"
Output "www/videos/workbench_terminal_demo.gif"

Set Shell "bash"
Set FontSize 15
Set Width 1360
Set Height 900
Set Padding 24
Set WindowBar Colorful
Set Theme "Catppuccin Mocha"
Set Framerate 30

# Initial title banner
Type "# Architecture 2.0: Grounded Micro-Loops Workbench"
Sleep 400ms
Enter
Type "# Workshop Demonstration: Verifying Physical Signoff Across 4 Loops"
Sleep 400ms
Enter
Sleep 1s

# Check containerized toolchain
Type "./arch2 docker run -- bash -c 'yosys -version && iverilog -v | head -n 1 && riscv64-linux-gnu-gcc --version | head -n 1'"
Sleep 600ms
Enter
Sleep 2s

# Run the master demonstration
Type "python3 labs/demo.py"
Sleep 600ms
Enter

# Allow demo execution and rich table rendering
Sleep 9s

# Concluding pause on the Grand Demonstration Matrix
Sleep 4s
