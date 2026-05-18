"""
Module 4 — ML Prediction
Time-aware training, labeling via future returns (ATR-based threshold),
LogisticRegression baseline + RandomForest + XGBoost.
Saves / loads model artifacts.  No data leakage.
"""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report

from config import settings
from core.feature_engineering import get_feature_columns
from utils.logger import get_logger

log = get_logger("ml_predictor")

LABEL_MAP = {0: "SELL", 1: "HOLD", 2: "BUY"}
LABEL_INV = {"SELL": 0, "HOLD": 1, "BUY": 2}


# ─────────────────────────────────────────────────────────────────────────────
# Labeling
# ─────────────────────────────────────────────────────────────────────────────

def create_labels(
    df: pd.DataFrame,
    future_bars: int = None,
    atr_mult: float = None,
) -> pd.Series:
    """
    Label = BUY  if future_return > +threshold
    Label = SELL if future_return < -threshold
    Label = HOLD otherwise

    threshold = atr_mult × ATR (scale-aware, avoids static pip thresholds)
    """
    future_bars = future_bars or settings.FUTURE_BARS
    atr_mult = atr_mult or settings.LABEL_THRESHOLD_ATR_MULT

    future_close = df["close"].shift(-future_bars)
    future_return = (future_close - df["close"]) / df["close"]

    if "atr" in df.columns:
        threshold = (df["atr"] / df["close"]) * atr_mult
    else:
        threshold = pd.Series(0.0005, index=df.index)

    labels = np.where(
        future_return > threshold, 2,           # BUY
        np.where(future_return < -threshold, 0, # SELL
                 1),                             # HOLD
    )
    return pd.Series(labels, index=df.index, name="label").astype(int)


# ─────────────────────────────────────────────────────────────────────────────
# Model artifact paths
# ─────────────────────────────────────────────────────────────────────────────

def _model_path(symbol: str, timeframe: str, name: str) -> Path:
    p = settings.MODELS_DIR / symbol / timeframe
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{name}.pkl"


def _meta_path(symbol: str, timeframe: str) -> Path:
    p = settings.MODELS_DIR / symbol / timeframe
    p.mkdir(parents=True, exist_ok=True)
    return p / "meta.json"


# ─────────────────────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────────────────────

def train_models(
    df: pd.DataFrame,
    symbol: str = "EURUSD",
    timeframe: str = "M15",
    feature_cols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Time-aware train/test split (no shuffling).
    Trains LR baseline + RandomForest + XGBoost (if available).
    Saves artifacts and returns evaluation summary.
    """
    feature_cols = feature_cols or get_feature_columns()

    # Add labels
    df = df.copy()
    df["label"] = create_labels(df)

    # Drop future rows that have NaN label (last future_bars rows)
    df = df.dropna(subset=feature_cols + ["label"])

    if len(df) < settings.MIN_CANDLES_REQUIRED:
        log.warning("Not enough data to train ({} rows)", len(df))
        return {"error": "insufficient_data", "rows": len(df)}

    # Time-aware split
    split_idx = int(len(df) * settings.TRAIN_TEST_RATIO)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]

    X_train = train[feature_cols].values
    y_train = train["label"].values.astype(int)
    X_test = test[feature_cols].values
    y_test = test["label"].values.astype(int)

    # Scale
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results: Dict[str, Any] = {
        "symbol": symbol, "timeframe": timeframe,
        "train_rows": len(train), "test_rows": len(test),
        "feature_cols": feature_cols,
        "label_counts": dict(zip(*np.unique(y_train, return_counts=True))),
    }

    trained_models: Dict[str, Any] = {}

    # ── Logistic Regression ────────────────────────────────────────────────
    lr = LogisticRegression(max_iter=1000, random_state=settings.RANDOM_STATE, class_weight="balanced")
    lr.fit(X_train_s, y_train)
    lr_preds = lr.predict(X_test_s)
    results["lr_report"] = classification_report(y_test, lr_preds, output_dict=True, zero_division=0)
    trained_models["lr"] = lr
    log.info("LR trained — accuracy: {:.2f}", results["lr_report"]["accuracy"])

    # ── Random Forest ──────────────────────────────────────────────────────
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=5,
        random_state=settings.RANDOM_STATE, class_weight="balanced", n_jobs=-1,
    )
    rf.fit(X_train, y_train)   # RF doesn't need scaling
    rf_preds = rf.predict(X_test)
    results["rf_report"] = classification_report(y_test, rf_preds, output_dict=True, zero_division=0)
    trained_models["rf"] = rf
    log.info("RF trained — accuracy: {:.2f}", results["rf_report"]["accuracy"])

    # ── XGBoost ────────────────────────────────────────────────────────────
    try:
        import xgboost as xgb
        xgb_model = xgb.XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            use_label_encoder=False, eval_metric="mlogloss",
            random_state=settings.RANDOM_STATE, verbosity=0,
        )
        xgb_model.fit(X_train, y_train)
        xgb_preds = xgb_model.predict(X_test)
        results["xgb_report"] = classification_report(y_test, xgb_preds, output_dict=True, zero_division=0)
        trained_models["xgb"] = xgb_model
        log.info("XGBoost trained — accuracy: {:.2f}", results["xgb_report"]["accuracy"])
    except ImportError:
        log.info("XGBoost not installed — skipping")

    # ── Save artifacts ─────────────────────────────────────────────────────
    for name, model in trained_models.items():
        with open(_model_path(symbol, timeframe, name), "wb") as f:
            pickle.dump(model, f)

    with open(_model_path(symbol, timeframe, "scaler"), "wb") as f:
        pickle.dump(scaler, f)

    meta = {
        "symbol": symbol,
        "timeframe": timeframe,
        "feature_cols": feature_cols,
        "trained_models": list(trained_models.keys()),
        "train_rows": len(train),
        "test_rows": len(test),
    }
    with open(_meta_path(symbol, timeframe), "w") as f:
        json.dump(meta, f, indent=2)

    results["models_saved"] = list(trained_models.keys())
    log.info("Models saved for {} {}", symbol, timeframe)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Inference
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    signal: str           # BUY | SELL | HOLD
    confidence: float     # 0.0 – 1.0
    probabilities: Dict[str, float] = None
    model_used: str = ""
    feature_importance: Dict[str, float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _load_model(symbol: str, timeframe: str, name: str):
    path = _model_path(symbol, timeframe, name)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def _load_meta(symbol: str, timeframe: str) -> Optional[dict]:
    path = _meta_path(symbol, timeframe)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def predict(
    df: pd.DataFrame,
    symbol: str = "EURUSD",
    timeframe: str = "M15",
    model_preference: str = "xgb",   # xgb | rf | lr
) -> PredictionResult:
    """
    Run inference on the latest bar of df.
    Tries preferred model, falls back in order: xgb → rf → lr.
    Auto-trains if no model artifacts exist.
    """
    meta = _load_meta(symbol, timeframe)

    if meta is None:
        log.info("No model found for {} {} — training now", symbol, timeframe)
        train_models(df, symbol, timeframe)
        meta = _load_meta(symbol, timeframe)

    if meta is None:
        return PredictionResult(signal="HOLD", confidence=0.0, model_used="none")

    feature_cols = meta.get("feature_cols", get_feature_columns())
    available = meta.get("trained_models", [])

    scaler = _load_model(symbol, timeframe, "scaler")

    # Choose model
    order = [model_preference] + ["xgb", "rf", "lr"]
    model = None
    model_name = ""
    for pref in order:
        if pref in available:
            model = _load_model(symbol, timeframe, pref)
            if model is not None:
                model_name = pref
                break

    if model is None:
        return PredictionResult(signal="HOLD", confidence=0.0, model_used="none")

    # Prepare feature row — last complete bar
    row = df[feature_cols].dropna().tail(1)
    if row.empty:
        log.warning("No complete feature row for prediction")
        return PredictionResult(signal="HOLD", confidence=0.0, model_used=model_name)

    X = row.values
    if scaler and model_name == "lr":
        X = scaler.transform(X)

    proba = model.predict_proba(X)[0]
    pred_idx = int(proba.argmax())
    confidence = float(proba[pred_idx])
    signal = LABEL_MAP[pred_idx]

    prob_dict = {LABEL_MAP[i]: float(proba[i]) for i in range(len(proba))}

    # Feature importance (RF / XGB)
    fi = None
    if hasattr(model, "feature_importances_"):
        fi = dict(zip(feature_cols, model.feature_importances_.tolist()))
        fi = dict(sorted(fi.items(), key=lambda x: x[1], reverse=True)[:10])

    log.info("Prediction: {} ({:.0%} confidence) via {}", signal, confidence, model_name)
    return PredictionResult(
        signal=signal,
        confidence=confidence,
        probabilities=prob_dict,
        model_used=model_name,
        feature_importance=fi,
    )


def models_exist(symbol: str, timeframe: str) -> bool:
    return _meta_path(symbol, timeframe).exists()
