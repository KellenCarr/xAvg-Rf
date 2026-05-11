.PHONY: install seed run demo clean verify

PORT ?= 8765
REGISTRY ?= $(CURDIR)/registry
SAMPLE ?= $(CURDIR)/sample-project

install:
	pip install -e .

seed:
	SKILLHUB_REGISTRY=$(REGISTRY) python -m skillhub.storage --seed $(CURDIR)/seed

run:
	SKILLHUB_REGISTRY=$(REGISTRY) uvicorn skillhub.api.main:app --host 0.0.0.0 --port $(PORT) --reload

demo: seed
	@echo "Visit http://localhost:$(PORT)/ (user) or http://localhost:$(PORT)/?role=admin (admin)"
	$(MAKE) run

clean:
	rm -rf $(REGISTRY)/acme $(REGISTRY)/platform $(REGISTRY)/community
	rm -f $(REGISTRY)/index.json $(REGISTRY)/audit.log.jsonl

verify:
	bash $(CURDIR)/scripts/verify.sh
