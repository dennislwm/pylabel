.PHONY: help install status run dry-run test clean stage-ledger run-ledger dry-ledger
SHELL := /bin/bash

CSV      ?= input/cards.csv
PRINTER  ?= HP_LaserJet_M211dw__486E30__20221016133708
OUT      ?= output
TEMPLATE ?= templates/avery_l7161_a4_18.html
TAIL     ?=
FORCE    ?=
OFFSET   ?= 0
TAIL_ARG  = $(if $(TAIL),--tail $(TAIL),)
FORCE_ARG = $(if $(FORCE),--force,)

help:
	@echo ""
	@echo "=== Ledger Workflow ==="
	@echo "  1. (curate in Coda -- tick Printed on rows already printed)"
	@echo "  2. make stage-ledger [TAIL=30]   Export from Coda + convert to input/ledger.csv (Printed rows excluded)"
	@echo "  3. make dry-ledger               Generate PDF without printing"
	@echo "  4. make run-ledger               Print"
	@echo ""
	@echo "=== Targets ==="
	@echo "  help           Show this help"
	@echo "  install        pipenv install from Pipfile"
	@echo "  status         Check system dependencies and printer"
	@echo "  stage-ledger   Export Ledger from Coda + convert to input/ledger.csv"
	@echo "  dry-ledger     Run pipeline on input/ledger.csv without printing"
	@echo "  run-ledger     Run pipeline on input/ledger.csv and print"
	@echo "  run            Run pipeline (CSV=input/cards.csv PRINTER=... OUT=output)"
	@echo "  dry-run        Run pipeline without printing (CSV=input/cards.csv OUT=output)"
	@echo "  test           Run test suite"
	@echo "  clean          Remove pipenv venv, __pycache__, and output PDFs"
	@echo ""

stage-ledger:
	cd ../13coda-cli/app && pipenv run python coda.py export-table --doc ytHmIeSU62 --table grid-vl71OA93BQ --output output/ledger.csv
	pipenv run python app/convert.py --mapping mappings/trackmycollection_pylabel_ledger.json --input ../13coda-cli/app/output/ledger.csv --output input/ledger.csv $(TAIL_ARG)

dry-ledger:
	pipenv run python app/pipeline.py --csv input/ledger.csv --template $(TEMPLATE) --out $(OUT) --offset $(OFFSET) --force

run-ledger:
	pipenv run python app/pipeline.py --csv input/ledger.csv --template $(TEMPLATE) --printer $(PRINTER) --out $(OUT) --offset $(OFFSET) $(FORCE_ARG)

install:
	pipenv install

status:
	@export PRINTER=$(PRINTER); source ./make.sh && show_status

run:
	pipenv run python app/pipeline.py --csv $(CSV) --template $(TEMPLATE) --printer $(PRINTER) --out $(OUT) --offset $(OFFSET)

dry-run:
	pipenv run python app/pipeline.py --csv $(CSV) --template $(TEMPLATE) --out $(OUT) --offset $(OFFSET)

test:
	pipenv run pytest tests/

clean:
	pipenv --rm; rm -rf __pycache__ output/*.pdf
