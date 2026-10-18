"""Cross-validation, metrics and learning curves.

Folds come from StratifiedGroupKFold with assignment_id as the group, so rows
from one assignment never end up on both sides of a split.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import LinearSVC
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, f1_score

def make_models(seed=0):
    return {
        "majority": make_pipeline(CountVectorizer(), DummyClassifier(strategy="most_frequent")),
        "nb_counts": make_pipeline(CountVectorizer(min_df=2, ngram_range=(1, 2), stop_words="english"),
                                   MultinomialNB(alpha=0.5)),
        "logreg_tfidf": make_pipeline(TfidfVectorizer(min_df=2, ngram_range=(1, 2), sublinear_tf=True, stop_words="english"),
                                      LogisticRegression(C=5.0, max_iter=2000, class_weight="balanced")),
        "tree_tfidf": make_pipeline(TfidfVectorizer(min_df=2, stop_words="english"),
                                    DecisionTreeClassifier(max_depth=12, min_samples_leaf=2, random_state=seed, class_weight="balanced")),
        "svm_tfidf": make_pipeline(TfidfVectorizer(min_df=2, ngram_range=(1, 2), sublinear_tf=True, stop_words="english"),
                                   LinearSVC(C=0.5, class_weight="balanced")),
    }

def _scores(model, X):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)
    if hasattr(model, "decision_function"):
        d = model.decision_function(X)
        return d if d.ndim == 2 else np.c_[-d, d]
    return None

def hit_at_k(y_true, scores, classes, k=3):
    """Hit@k = fraction of rows whose true label is in the top-k scored labels."""
    if scores is None:
        return np.nan
    top = np.argsort(-scores, axis=1)[:, :k]
    cls = np.asarray(classes)
    return float(np.mean([t in cls[row] for t, row in zip(y_true, top)]))

def family_consistency(y_true, y_pred, tag2family):
    """Fraction of predictions whose family matches the true tag's family."""
    return float(np.mean([tag2family.get(a) == tag2family.get(b) for a, b in zip(y_true, y_pred)]))

def cross_validate(texts, labels, groups, model, n_splits=5, seed=0, tag2family=None, k=3):
    texts, labels, groups = np.asarray(texts), np.asarray(labels), np.asarray(groups)
    skf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    y_true_all, y_pred_all, fold_rows = [], [], []
    for fold, (tr, te) in enumerate(skf.split(texts, labels, groups)):
        model.fit(texts[tr], labels[tr])
        pred = model.predict(texts[te])
        sc = _scores(model, texts[te])
        classes = model.classes_ if hasattr(model, "classes_") else model[-1].classes_
        row = dict(fold=fold, n_test=len(te),
                   accuracy=accuracy_score(labels[te], pred),
                   macro_f1=f1_score(labels[te], pred, average="macro", zero_division=0),
                   hit_at_k=hit_at_k(labels[te], sc, classes, k))
        if tag2family:
            row["family_consistency"] = family_consistency(labels[te], pred, tag2family)
        fold_rows.append(row)
        y_true_all.extend(labels[te]); y_pred_all.extend(pred)
    folds = pd.DataFrame(fold_rows)
    summary = folds.drop(columns=["fold", "n_test"]).agg(["mean", "std"])
    return summary, folds, np.array(y_true_all), np.array(y_pred_all)

def learning_curve(texts, labels, groups, model_fn, fractions=(0.2, 0.4, 0.6, 0.8, 1.0), n_splits=5, seed=0):
    """Macro-F1 on the held-out fold as a function of the fraction of the training fold used."""
    texts, labels, groups = np.asarray(texts), np.asarray(labels), np.asarray(groups)
    skf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    rng = np.random.default_rng(seed)
    out = []
    for fold, (tr, te) in enumerate(skf.split(texts, labels, groups)):
        for f in fractions:
            idx = rng.choice(tr, size=max(int(len(tr) * f), 10), replace=False)
            if len(set(labels[idx])) < 2:
                continue
            m = model_fn(); m.fit(texts[idx], labels[idx])
            out.append(dict(fold=fold, fraction=f, n_train=len(idx),
                            train_f1=f1_score(labels[idx], m.predict(texts[idx]), average="macro", zero_division=0),
                            test_f1=f1_score(labels[te], m.predict(texts[te]), average="macro", zero_division=0)))
    return pd.DataFrame(out)

def top_words_nb(model, classes_of_interest=None, n=12):
    """Per-class most indicative words from a fitted CountVectorizer+MultinomialNB pipeline,
    ranked by log P(w|c) - mean_c' log P(w|c')."""
    vec, nb = model[0], model[-1]
    vocab = np.array(vec.get_feature_names_out())
    logp = nb.feature_log_prob_
    rows = {}
    for i, c in enumerate(nb.classes_):
        if classes_of_interest and c not in classes_of_interest:
            continue
        score = logp[i] - logp.mean(axis=0)
        rows[c] = list(vocab[np.argsort(-score)[:n]])
    return rows
