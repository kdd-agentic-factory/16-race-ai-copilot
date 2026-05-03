#!/usr/bin/env bash
set -euo pipefail

ollama pull qwen2.5:7b
ollama pull mistral:7b
ollama pull qwen2.5-coder:7b
