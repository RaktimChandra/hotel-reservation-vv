# Common tasks. On Windows run the commands directly (see README) or use `make` from Git Bash.
PY ?= python

.PHONY: install test smoke security e2e demo live coverage lint check perf mutation seed docs rtm clean

install:            ## install Python deps and Chromium
	$(PY) -m pip install -r requirements.txt
	$(PY) -m playwright install chromium

test:               ## run all 554 test cases
	$(PY) -m pytest -q

smoke security e2e: ## run one marker group with live test-case output
	$(PY) -m pytest -q --tc -m $@

live:               ## guided live demo (visible browser for the E2E stage)
	$(PY) tools/live_demo.py

demo:               ## start the app on port 8765
	$(PY) -m uvicorn app.main:app --reload --port 8765

coverage:           ## statement + branch coverage with HTML report
	$(PY) -m pytest -q --cov=app --cov-branch --cov-report=term --html=reports/test_report.html --self-contained-html

lint:               ## static analysis
	ruff check app tests tools
	bandit -q -r app -lll

check:              ## packaging / release checks
	$(PY) tools/check_package.py

perf:               ## load, stress, spike, soak, volume
	$(PY) tools/perf_test.py

mutation:           ## mutation testing (~5 min)
	$(PY) tools/mutation.py

seed:               ## fault seeding
	$(PY) tools/fault_seeding.py

rtm:                ## regenerate docs/TRACEABILITY.md
	$(PY) tools/make_traceability.py

docs:               ## regenerate every document (needs Node 18+ and LibreOffice)
	npm install
	$(PY) tools/make_workbook.py
	$(PY) tools/doc/toc_pass.py tools/doc/report.js deliverables/HRRS_VV_Test_Report_Raktim.docx
	node tools/doc/companions.js
	node tools/deck/deck.js
	$(PY) tools/make_dashboard.py
	$(PY) tools/make_onepager.py

clean:
	rm -rf .pytest_cache .ruff_cache .hypothesis reports/results_partial.json reports/e2e_videos
