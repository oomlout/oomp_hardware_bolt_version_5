PYTHON ?= python
ARGS ?=

.PHONY: all
all:
	$(PYTHON) -X utf8 action_make_all.py $(ARGS)
