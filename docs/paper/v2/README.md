# v2 paper (draft)

`main.tex` is a companion paper on what changed in ScamGuard v2. Every number comes from `numbers.tex`, which
`make_numbers.py` generates from `backend/ml_training/research/results_v2.json`:

    cd backend && python -m ml_training.research.v2_experiments && cd ..
    python docs/paper/v2/make_numbers.py
    cd docs/paper/v2 && latexmk -pdf main.tex

Before posting it anywhere public (e.g. arXiv), check the preprint and anonymity policy of COMP-SIF 2027, where the
v1 paper (Paper ID 1206) is under double-blind review.
