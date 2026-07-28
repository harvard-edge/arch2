SHELL := /bin/sh

DECK := architecture-2.0
LATEXMK := latexmk

.PHONY: all clean

all: $(DECK).pdf

$(DECK).pdf: $(DECK).tex
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error $(DECK).tex

clean:
	$(LATEXMK) -C $(DECK).tex
