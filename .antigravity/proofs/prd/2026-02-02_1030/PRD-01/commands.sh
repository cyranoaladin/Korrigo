#!/bin/bash
# PRD-01: Baseline - Pré-flight commands

git status --porcelain
git pull --ff-only origin main
git rev-parse --short HEAD
git tag prd-safe-20260202-1030-baseline 73d2dc3
