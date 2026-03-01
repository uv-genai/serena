#!/usr/bin/env bash
#git remote add serena-orig https://github.com/oraios/serena
git fetch serena-orig
git merge serena-orig/main --allow-unrelated-histories -m"Sync with original"
git push
