# The AI Engineer's Library — examples

Runnable code for the books in **The AI Engineer's Library** by Gabriel Anhaia.

| Book | Directory | Status |
|---|---|---|
| *Inference in Production* | [`inference-in-production/`](inference-in-production/) | Being written — this fills in as the book is drafted. |

Each book has its own directory, and each directory stands on its own: you can start with any
book without running the others.

Each book is one Docker Compose service, and every example runs with one command and no local
toolchain beyond Docker:

```sh
docker compose run --rm inference-in-production ch00
```

The book's directory README lists its labs and what each needs.

## What is here, and what is not

This repository holds **code only**: the labs, scripts and configuration the books print. The
books explain why the code is shaped the way it is; this repository shows what to run. The books
themselves are separate copyrighted works, and no manuscript text appears here.

## Versions

Every dependency is pinned to an exact version. [`docs/versions.md`](docs/versions.md) records
each pin, why it was chosen, and the date it was last verified. The scheduled CI runs every
example against those pins, and a second job runs them against the latest releases so a breaking
upstream change shows up here before it shows up in a reader's terminal.

## License

MIT — see [LICENSE](LICENSE). The license covers the code in this repository only.
