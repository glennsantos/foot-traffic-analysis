PYTHON ?= python3

.PHONY: package clean

package:
	$(PYTHON) scripts/package.py

clean:
	rm -rf dist __pycache__ */__pycache__
	rm -rf cache analyses analyses_new reports
	rm -f app.log

