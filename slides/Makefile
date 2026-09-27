SHELL := /bin/sh

DECKS := architecture-2.0 workshop-slides catalog
LATEXMK := latexmk

.PHONY: all clean

all: $(addsuffix .pdf, $(DECKS))

%.pdf: %.tex
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error $<

clean:
	$(LATEXMK) -C $(addsuffix .tex, $(DECKS))
