# Every target delegates to tasks.py so the same commands work on Windows without make:
#   python tasks.py <target>
ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python.exe
else
PY := .venv/bin/python
endif

TARGETS := network demand toy baselines bench train eval figures replays export \
           web-dev web-build demo test all

.PHONY: setup $(TARGETS)

setup:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) tasks.py setup

$(TARGETS):
	$(PY) tasks.py $@
