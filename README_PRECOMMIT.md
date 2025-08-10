# Pre-commit Pack (flake8 + mypy + security + notebooks)

## Install
```bash
poetry add --dev pre-commit
poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
# Initial baseline for secrets (optional: refresh later)
poetry run detect-secrets scan > .secrets.baseline
poetry run pre-commit run --all-files
```
## Tips
- Adjust the paths in the `bandit` hooks and `exclude` to match your actual layout (e.g., `backend/`, `project/src/`).
- Notebooks are expected in `project/research/` or `notebooks/`. Change the pattern if yours are stored elsewhere.
- If mypy is too strict, consider relaxing `disallow_untyped_defs` or add intentional `type: ignore` comments.
