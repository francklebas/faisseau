# Revue quotidienne — commandes du dépôt.
#   make            installe, lance le pipeline, génère le site et le sert en local
#   make quotidien  passage planifiable : pipeline + génération du site, sans serveur
.NOTPARALLEL:
.DEFAULT_GOAL := revue

PORT ?= 4173
SITE := web/.output/public

.PHONY: revue installer pipeline site servir quotidien test flux sujets affinites comparer-embeddings deployer

revue: installer pipeline site servir

installer:
	uv sync
	cd web && pnpm install --frozen-lockfile

pipeline:
	uv run revue executer

site:
	cd web && pnpm generate

servir:
	@echo "Revue quotidienne : http://localhost:$(PORT)  (Ctrl+C pour arrêter)"
	uv run python -m http.server $(PORT) --directory $(SITE) --bind 127.0.0.1

# Passage quotidien : n'installe rien, ne sert rien, sort en erreur si une étape échoue
# (y compris si le LLM configuré est injoignable : mieux vaut garder l'édition de la veille).
# Fournisseur par défaut : celui de config/reglages.yaml (Mistral). Repli local, à demander
# explicitement : make quotidien LLM=koboldcpp
quotidien:
	$(if $(LLM),REVUE_LLM=$(LLM) )uv run revue executer --exiger-llm
	cd web && pnpm generate

test:
	uv run pytest -q

flux:
	uv run revue flux

sujets:
	uv run revue sujets

affinites:
	uv run revue affinites

comparer-embeddings:
	uv run python scripts/comparer_embeddings.py --avec-extraits

# Publication sur Cloudflare (nécessite un compte et `wrangler login`). Jamais lancé automatiquement.
deployer:
	cd web && pnpm dlx wrangler deploy
