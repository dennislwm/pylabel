.PHONY: help install status run dry-run clean
SHELL := /bin/bash

CSV     ?= input/cards.csv
PRINTER ?= HP_LaserJet_M211dw__486E30__20221016133708
OUT     ?= output

help:
	@echo ""
	@echo "=== Targets ==="
	@echo "  help       Show this help"
	@echo "  install    pipenv install from Pipfile"
	@echo "  status     Check system dependencies and printer"
	@echo "  run        Run pipeline (CSV=input/cards.csv PRINTER=HP_LaserJet_M211dw... OUT=output)"
	@echo "  dry-run    Run pipeline without printing (CSV=input/cards.csv OUT=output)"
	@echo "  clean      Remove pipenv venv, __pycache__, and output PDFs"
	@echo ""

install:
	pipenv install

status:
	@export PRINTER=$(PRINTER); source ./make.sh && show_status

run:
	pipenv run python app/pipeline.py --csv $(CSV) --printer $(PRINTER) --out $(OUT)

dry-run:
	pipenv run python app/pipeline.py --csv $(CSV) --out $(OUT)

clean:
	pipenv --rm; rm -rf __pycache__ output/*.pdf
