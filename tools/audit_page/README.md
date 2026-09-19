# Audit page

One self-contained HTML file to review every decision of a batch by hand: the original
PDF, the decision, the reason the engine recorded, all the rules with their verdict, the
symbols read and the source rows each rule compared against.

```bash
make setup && make erp && make demo        # a decided process to read
uv run --project backend python tools/audit_page/build.py \
  --outcomes ~/la-caja-outcomes/outcomes.jsonl \
  --output output/audit.html
```

`--outcomes` is the delivered file, shown beside this machine's own decision so the two
can be compared; omit it to show only this machine's. The page needs no server: open the
file. It embeds every PDF of the batch, so it weighs about 12 MB for batch 1 and is
written to `output/`, which Git ignores. Do not commit a built page.

Publishing it as a Claude Artifact adds shared review marks (`db` and `user`
capabilities): each reviewer's ok / wrong / unsure and note is stored per file and
visible to everyone who opens the page.
