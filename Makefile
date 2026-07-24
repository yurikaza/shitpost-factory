.PHONY: setup check run publish cron test lint clean doctor

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

setup:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	@$(MAKE) check

check:
	@command -v ffmpeg >/dev/null || (echo "MISSING: ffmpeg not on PATH" && exit 1)
	@command -v ffprobe >/dev/null || (echo "MISSING: ffprobe not on PATH" && exit 1)
	@test -f .env || (echo "MISSING: .env - copy .env.example" && exit 1)
	@ls assets/fonts/*.ttf >/dev/null 2>&1 || echo "WARN: no .ttf in assets/fonts - captions will fail"
	@echo "environment ok"

doctor:
	$(PY) -m factory.cli doctor

# make run CONCEPT=text-pov
run:
	$(PY) -m factory.cli run --concept $(CONCEPT)

# make run-dry CONCEPT=text-pov  (render only, no publish even if DRY_RUN=false)
run-dry:
	DRY_RUN=true $(PY) -m factory.cli run --concept $(CONCEPT)

publish:
	DRY_RUN=false $(PY) -m factory.cli run --concept $(CONCEPT) --publish

# produce one video for every enabled concept - what cron calls
cron:
	$(PY) -m factory.cli run-all --publish

test:
	$(VENV)/bin/pytest -q

lint:
	$(VENV)/bin/ruff check src tests

clean:
	rm -rf work/* && touch work/.gitkeep
