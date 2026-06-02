PYTHON ?= python3

MOCK_DIR ?= reports/mock-runs
REGENERATED_DIR ?= reports/mock-runs-regenerated
DIAGNOSIS_DIR ?= reports/mock-diagnosis
COMPARE_DIR ?= reports/mock-compare
PREVIEW_DIR ?= reports/local-preview
WEB_HOST ?= 127.0.0.1
WEB_PORT ?= 8000

.PHONY: test demo preview real diagnose compare web

test:
	$(PYTHON) -m unittest

demo: test
	$(PYTHON) -m packetscope experiment --mock --runs 3 --out $(MOCK_DIR)
	$(PYTHON) -m packetscope report $(MOCK_DIR)/results.json --out $(REGENERATED_DIR)
	$(PYTHON) -m packetscope diagnose $(MOCK_DIR)/results.json --out $(DIAGNOSIS_DIR)
	$(PYTHON) -m packetscope compare $(MOCK_DIR)/results.json $(REGENERATED_DIR)/results.json --out $(COMPARE_DIR)

preview:
	$(PYTHON) -m packetscope experiment --mock --runs 3 --out $(PREVIEW_DIR)
	$(PYTHON) -m http.server 8000 --bind 127.0.0.1

real:
	$(PYTHON) -m packetscope experiment example.com cloudflare.com wikipedia.org github.com python.org --runs 3 --trace-wait 1 --trace-timeout 25 --out reports/real-runs

diagnose:
	$(PYTHON) -m packetscope diagnose $(MOCK_DIR)/results.json --out $(DIAGNOSIS_DIR)

compare:
	$(PYTHON) -m packetscope compare $(MOCK_DIR)/results.json $(REGENERATED_DIR)/results.json --out $(COMPARE_DIR)

web:
	$(PYTHON) -m packetscope web --host $(WEB_HOST) --port $(WEB_PORT)
