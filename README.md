# CS156 Pipeline 1

Classifying HC/LO tags from the footnotes of my Minerva assignment submissions.

## Layout

```
data/inventory.tsv            submitted assignments (id, course, title, due date, Forum resource ids)
data/processed/sections.csv   one row per tag application: tag, source, justification text, context text
data/raw/                     submission PDFs (not committed)
src/forum_download.py         scrapes my submitted assignments and PDFs from Forum (needs a session cookie)
src/extract_sections.py       PDFs -> sections.csv (footnote marker linking)
src/tags.py                   tag normalisation, HC -> cornerstone family rule, masking vocabulary
src/dataset.py                modelling table and masking
src/evaluate.py               grouped cross-validation, hit@k, family consistency, learning curves
src/make_diagram.py           pipeline figure
notebooks/pipeline.ipynb      experiments (executed)
figures/                      output figures
```

## Run

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/extract_sections.py          # optional, needs data/raw/<COURSE>/*.pdf
python src/make_diagram.py
jupyter nbconvert --to notebook --execute --inplace notebooks/pipeline.ipynb
```

`sections.csv` is committed, so the notebook runs without the PDFs.
