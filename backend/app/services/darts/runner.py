"""
Darts anomaly detection runner.

Converts pandas DataFrames into Darts TimeSeries, instantiates the appropriate
scorer or forecasting model, runs detection, and maps results back to our schema.
"""

import logging
import math
from collections import defaultdict
from typing import Callable

import numpy as np
import pandas as pd
from darts import TimeSeries
from darts.ad.scorers import KMeansScorer, WassersteinScorer
from darts.ad.detectors import QuantileDetector, ThresholdDetector, IQRDetector

from ...models.enums import DartsModelId

# Global forecast models use a different pipeline (fit once, predict without retraining)
GLOBAL_FORECAST_MODELS = {
    DartsModelId.LINEAR_REGRESSION, DartsModelId.RANDOM_FOREST,
    DartsModelId.LIGHTGBM, DartsModelId.XGBOOST,
    DartsModelId.NBEATS, DartsModelId.NHITS, DartsModelId.TFT,
    DartsModelId.DLINEAR, DartsModelId.NLINEAR, DartsModelId.TCN,
    DartsModelId.TRANSFORMER, DartsModelId.BLOCK_RNN,
    DartsModelId.TIDE, DartsModelId.TSMIXER,
    DartsModelId.CHRONOS2, DartsModelId.TIMESFM,
}

# Foundation models (pre-trained, HuggingFace Hub) — used for progress messaging
FOUNDATION_MODELS = {
    DartsModelId.CHRONOS2, DartsModelId.TIMESFM, DartsModelId.TSPULSE,
    DartsModelId.MOMENT, DartsModelId.LAG_LLAMA,
}

# Number of timesteps to predict per forward pass for foundation models.
# TimesFM always computes 128 output steps internally, so using 128 is
# optimal (no wasted compute). Chronos2 also benefits from larger chunks.
FOUNDATION_CHUNK_SIZE = 128
from ...models.schemas import (
    DartsDetectionConfig,
    DartsAnomalyPoint,
    DartsAnomalyResult,
    ForecastPoint,
    AnomalyRegion,
    AnomalySummary,
)

logger = logging.getLogger(__name__)


def _get_accelerator() -> str:
    """Return best available PyTorch accelerator."""
    try:
        import torch
        if torch.backends.mps.is_available():
            logger.info("PyTorch accelerator: MPS (Apple Silicon GPU)")
            return "mps"
        if torch.cuda.is_available():
            logger.info("PyTorch accelerator: CUDA")
            return "cuda"
    except (ImportError, AttributeError):
        pass
    logger.info("PyTorch accelerator: CPU")
    return "cpu"


# Cache the accelerator at import time to avoid repeated torch imports
_ACCELERATOR: str | None = None


def _cached_accelerator() -> str:
    global _ACCELERATOR
    if _ACCELERATOR is None:
        _ACCELERATOR = _get_accelerator()
    return _ACCELERATOR


def build_scorer(model_id: str, params: dict):
    """Build a Darts AnomalyScorer from model_id and user params."""
    window = max(1, int(params.get("window", 10)))

    contam = float(params.get("contamination", 0.1))

    if model_id == DartsModelId.KMEANS:
        return KMeansScorer(
            window=window,
            k=int(params.get("k", 8)),
        )
    elif model_id == DartsModelId.ISOLATION_FOREST:
        from pyod.models.iforest import IForest
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=IForest(n_estimators=int(params.get("n_estimators", 100)),
                          contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.LOF:
        from pyod.models.lof import LOF
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=LOF(n_neighbors=int(params.get("n_neighbors", 20)),
                      contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.ECOD:
        from pyod.models.ecod import ECOD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=ECOD(contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.WASSERSTEIN:
        return WassersteinScorer(
            window=window,
        )
    elif model_id == DartsModelId.COPOD:
        from pyod.models.copod import COPOD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=COPOD(contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.HBOS:
        from pyod.models.hbos import HBOS
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=HBOS(n_bins=int(params.get("n_bins", 10)),
                       contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.KNN:
        from pyod.models.knn import KNN
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=KNN(n_neighbors=int(params.get("n_neighbors", 20)),
                      contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.OCSVM:
        from pyod.models.ocsvm import OCSVM
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=OCSVM(kernel=str(params.get("kernel", "rbf")),
                        nu=contam),
            window=window,
        )
    elif model_id == DartsModelId.INNE:
        from pyod.models.inne import INNE
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=INNE(n_estimators=int(params.get("n_estimators", 200)),
                       contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.LODA:
        from pyod.models.loda import LODA
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=LODA(n_bins=int(params.get("n_bins", 10)),
                       n_random_cuts=int(params.get("n_random_cuts", 100)),
                       contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.CBLOF:
        from pyod.models.cblof import CBLOF
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=CBLOF(n_clusters=int(params.get("n_clusters", 8)),
                        alpha=float(params.get("alpha", 0.9)),
                        contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.ROD:
        from pyod.models.rod import ROD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=ROD(contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.ABOD:
        from pyod.models.abod import ABOD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=ABOD(n_neighbors=int(params.get("n_neighbors", 10)),
                        method=str(params.get("method", "fast")),
                        contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.SOS:
        from pyod.models.sos import SOS
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=SOS(perplexity=float(params.get("perplexity", 4.5)),
                      contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.LSCP:
        from pyod.models.lof import LOF
        from pyod.models.iforest import IForest
        from pyod.models.ocsvm import OCSVM as OCSVM_
        from pyod.models.lscp import LSCP
        from darts.ad.scorers import PyODScorer
        base = [LOF(), IForest(), OCSVM_()]
        return PyODScorer(
            model=LSCP(detector_list=base, contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.SOD:
        from pyod.models.sod import SOD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=SOD(n_neighbors=int(params.get("n_neighbors", 20)),
                       ref_set=int(params.get("ref_set", 10)),
                       contamination=contam),
            window=window,
        )
    elif model_id == DartsModelId.DEEP_SVDD:
        from pyod.models.deep_svdd import DeepSVDD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=DeepSVDD(
                n_features=window,
                epochs=int(params.get("epochs", 30)),
                contamination=float(params.get("contamination", 0.05)),
            ),
            window=window,
        )
    elif model_id == DartsModelId.AUTOENCODER:
        from pyod.models.auto_encoder import AutoEncoder
        from darts.ad.scorers import PyODScorer
        hidden_str = str(params.get("hidden_neurons", "64,32,32,64"))
        hidden = [int(x.strip()) for x in hidden_str.split(",")]
        return PyODScorer(
            model=AutoEncoder(
                hidden_neuron_list=hidden,
                epoch_num=int(params.get("epochs", 30)),
                dropout_rate=float(params.get("dropout_rate", 0.2)),
                contamination=float(params.get("contamination", 0.05)),
            ),
            window=window,
        )
    elif model_id == DartsModelId.VAE:
        from pyod.models.vae import VAE
        from darts.ad.scorers import PyODScorer
        hidden_str = str(params.get("hidden_neurons", "64,32,32,64"))
        hidden = [int(x.strip()) for x in hidden_str.split(",")]
        mid = len(hidden) // 2
        return PyODScorer(
            model=VAE(
                encoder_neuron_list=hidden[:mid],
                decoder_neuron_list=hidden[mid:],
                latent_dim=int(params.get("latent_dim", 2)),
                epoch_num=int(params.get("epochs", 30)),
                contamination=contam,
            ),
            window=window,
        )
    elif model_id == DartsModelId.PCA:
        from pyod.models.pca import PCA
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=PCA(
                n_components=int(params.get("n_components", 5)),
                contamination=contam,
            ),
            window=window,
        )
    elif model_id == DartsModelId.MCD:
        from pyod.models.mcd import MCD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(
            model=MCD(
                support_fraction=float(params.get("support_fraction", 0.5)),
                contamination=contam,
            ),
            window=window,
        )
    else:
        raise ValueError(f"Unknown scorer model: {model_id}")


def build_forecast_model(model_id: str, params: dict):
    """Build a Darts local forecasting model."""
    if model_id == DartsModelId.EXPONENTIAL_SMOOTHING:
        from darts.models import ExponentialSmoothing
        return ExponentialSmoothing(
            seasonal_periods=int(params.get("seasonal_periods", 24)),
        )
    elif model_id == DartsModelId.FFT:
        from darts.models import FFT
        return FFT(
            nr_freqs_to_keep=int(params.get("nr_freqs_to_keep", 10)),
        )
    elif model_id == DartsModelId.THETA:
        from darts.models import Theta
        from darts.utils.utils import SeasonalityMode
        mode_map = {
            "multiplicative": SeasonalityMode.MULTIPLICATIVE,
            "additive": SeasonalityMode.ADDITIVE,
            "none": SeasonalityMode.NONE,
        }
        season_mode_str = str(params.get("season_mode", "multiplicative"))
        return Theta(
            theta=float(params.get("theta", 2.0)),
            season_mode=mode_map.get(season_mode_str, SeasonalityMode.MULTIPLICATIVE),
        )
    elif model_id == DartsModelId.ARIMA:
        from darts.models import ARIMA
        return ARIMA(
            p=int(params.get("p", 1)),
            d=int(params.get("d", 1)),
            q=int(params.get("q", 1)),
        )
    elif model_id == DartsModelId.FOUR_THETA:
        from darts.models import FourTheta
        from darts.utils.utils import SeasonalityMode
        mode_map = {
            "multiplicative": SeasonalityMode.MULTIPLICATIVE,
            "additive": SeasonalityMode.ADDITIVE,
            "none": SeasonalityMode.NONE,
        }
        season_mode_str = str(params.get("season_mode", "multiplicative"))
        return FourTheta(
            theta=float(params.get("theta", 2.0)),
            season_mode=mode_map.get(season_mode_str, SeasonalityMode.MULTIPLICATIVE),
        )
    elif model_id == DartsModelId.AUTO_ARIMA:
        from darts.models import AutoARIMA
        return AutoARIMA(
            season_length=int(params.get("season_length", 24)),
        )
    elif model_id == DartsModelId.NAIVE_MEAN:
        from darts.models import NaiveMean
        return NaiveMean()
    elif model_id == DartsModelId.NAIVE_SEASONAL:
        from darts.models import NaiveSeasonal
        return NaiveSeasonal(K=int(params.get("K", 24)))
    elif model_id == DartsModelId.NAIVE_DRIFT:
        from darts.models import NaiveDrift
        return NaiveDrift()
    elif model_id == DartsModelId.NAIVE_MOVING_AVG:
        from darts.models import NaiveMovingAverage
        return NaiveMovingAverage(
            input_chunk_length=int(params.get("input_chunk_length", 24)),
        )
    elif model_id == DartsModelId.CROSTON:
        from darts.models import Croston
        return Croston(
            version=str(params.get("version", "classic")),
        )
    elif model_id == DartsModelId.PROPHET:
        from darts.models import Prophet
        # Convert "auto"/"true"/"false" strings to Prophet's expected types
        def _prophet_bool(val):
            if val == "auto":
                return "auto"
            return val == "true"
        return Prophet(
            growth=str(params.get("growth", "linear")),
            changepoint_prior_scale=float(params.get("changepoint_prior_scale", 0.05)),
            seasonality_mode=str(params.get("seasonality_mode", "additive")),
            seasonality_prior_scale=float(params.get("seasonality_prior_scale", 10.0)),
            daily_seasonality=_prophet_bool(params.get("daily_seasonality", "auto")),
            weekly_seasonality=_prophet_bool(params.get("weekly_seasonality", "auto")),
            yearly_seasonality=_prophet_bool(params.get("yearly_seasonality", "auto")),
        )
    else:
        raise ValueError(f"Unknown forecast model: {model_id}")


def build_global_forecast_model(model_id: str, params: dict):
    """Build a Darts GlobalForecastingModel (LinearRegression, RandomForest)."""
    if model_id == DartsModelId.LINEAR_REGRESSION:
        from darts.models import LinearRegressionModel
        return LinearRegressionModel(
            lags=int(params.get("lags", 24)),
            output_chunk_length=1,
        )
    elif model_id == DartsModelId.RANDOM_FOREST:
        from darts.models import RandomForest
        return RandomForest(
            lags=int(params.get("lags", 24)),
            output_chunk_length=1,
            n_estimators=int(params.get("n_estimators", 100)),
            max_depth=int(params.get("max_depth", 10)),
        )
    elif model_id == DartsModelId.LIGHTGBM:
        from darts.models import LightGBMModel
        return LightGBMModel(
            lags=int(params.get("lags", 24)),
            output_chunk_length=1,
            n_estimators=int(params.get("n_estimators", 100)),
            max_depth=int(params.get("max_depth", 6)),
            learning_rate=float(params.get("learning_rate", 0.1)),
            verbose=-1,
        )
    elif model_id == DartsModelId.XGBOOST:
        from darts.models import XGBModel
        return XGBModel(
            lags=int(params.get("lags", 24)),
            output_chunk_length=1,
            n_estimators=int(params.get("n_estimators", 100)),
            max_depth=int(params.get("max_depth", 6)),
            learning_rate=float(params.get("learning_rate", 0.1)),
        )
    # --- Deep learning (torch) models ---
    # Common DL params
    _dl_icl = int(params.get("input_chunk_length", 24))
    _dl_epochs = int(params.get("n_epochs", 10))
    _dl_lr = float(params.get("learning_rate", 0.001))
    _dl_bs = int(params.get("batch_size", 32))
    _dl_dropout = float(params.get("dropout", 0.1))
    _dl_common = dict(
        input_chunk_length=_dl_icl,
        output_chunk_length=1,
        n_epochs=_dl_epochs,
        batch_size=_dl_bs,
        dropout=_dl_dropout,
        optimizer_kwargs={"lr": _dl_lr},
        pl_trainer_kwargs={"accelerator": _cached_accelerator(), "enable_progress_bar": False},
    )
    if model_id == DartsModelId.NBEATS:
        from darts.models import NBEATSModel
        return NBEATSModel(
            **_dl_common,
            num_stacks=int(params.get("num_stacks", 10)),
        )
    elif model_id == DartsModelId.NHITS:
        from darts.models import NHiTSModel
        return NHiTSModel(
            **_dl_common,
            num_stacks=int(params.get("num_stacks", 3)),
        )
    elif model_id == DartsModelId.TFT:
        from darts.models import TFTModel
        return TFTModel(
            **_dl_common,
            hidden_size=int(params.get("hidden_size", 16)),
        )
    elif model_id == DartsModelId.DLINEAR:
        from darts.models import DLinearModel
        return DLinearModel(**_dl_common)
    elif model_id == DartsModelId.NLINEAR:
        from darts.models import NLinearModel
        return NLinearModel(**_dl_common)
    elif model_id == DartsModelId.TCN:
        from darts.models import TCNModel
        return TCNModel(
            **_dl_common,
            num_filters=int(params.get("num_filters", 3)),
        )
    elif model_id == DartsModelId.TRANSFORMER:
        from darts.models import TransformerModel
        return TransformerModel(
            **_dl_common,
            d_model=int(params.get("d_model", 16)),
            nhead=int(params.get("nhead", 4)),
        )
    elif model_id == DartsModelId.BLOCK_RNN:
        from darts.models import BlockRNNModel
        return BlockRNNModel(
            **_dl_common,
            model=str(params.get("rnn_model", "LSTM")),
            hidden_dim=int(params.get("hidden_dim", 25)),
        )
    elif model_id == DartsModelId.TIDE:
        from darts.models import TiDEModel
        return TiDEModel(
            **_dl_common,
            hidden_size=int(params.get("hidden_size", 16)),
        )
    elif model_id == DartsModelId.TSMIXER:
        from darts.models import TSMixerModel
        return TSMixerModel(
            **_dl_common,
            hidden_size=int(params.get("hidden_size", 16)),
        )
    # --- Foundation models (pre-trained, HuggingFace Hub) ---
    elif model_id == DartsModelId.CHRONOS2:
        from darts.models import Chronos2Model
        return Chronos2Model(
            input_chunk_length=int(params.get("input_chunk_length", 64)),
            output_chunk_length=FOUNDATION_CHUNK_SIZE,
            hub_model_name=str(params.get("hub_model_name", "autogluon/chronos-2-small")),
        )
    elif model_id == DartsModelId.TIMESFM:
        from darts.models import TimesFM2p5Model
        return TimesFM2p5Model(
            input_chunk_length=int(params.get("input_chunk_length", 64)),
            output_chunk_length=FOUNDATION_CHUNK_SIZE,
        )
    else:
        raise ValueError(f"Unknown global forecast model: {model_id}")


def build_residual_scorer(scorer_id: str, params: dict):
    """Build a Darts scorer for evaluating forecast residuals via score_from_prediction."""
    window = max(1, int(params.get("scorer_window", 10)))

    if scorer_id == "difference":
        from darts.ad.scorers import DifferenceScorer
        return DifferenceScorer()
    elif scorer_id == "norm":
        from darts.ad.scorers import NormScorer
        return NormScorer(ord=1, window=window)
    elif scorer_id == "kmeans":
        return KMeansScorer(window=window, k=int(params.get("scorer_k", 8)))
    elif scorer_id == "wasserstein":
        return WassersteinScorer(window=window)
    elif scorer_id == "pyod_iforest":
        from pyod.models.iforest import IForest
        from darts.ad.scorers import PyODScorer
        return PyODScorer(model=IForest(), window=window)
    elif scorer_id == "pyod_lof":
        from pyod.models.lof import LOF
        from darts.ad.scorers import PyODScorer
        return PyODScorer(model=LOF(), window=window)
    elif scorer_id == "pyod_copod":
        from pyod.models.copod import COPOD
        from darts.ad.scorers import PyODScorer
        return PyODScorer(model=COPOD(), window=window)
    elif scorer_id == "pyod_knn":
        from pyod.models.knn import KNN
        from darts.ad.scorers import PyODScorer
        return PyODScorer(model=KNN(), window=window)
    return None


def build_detector(detector_type: str, threshold: float):
    """Build a Darts binary detector."""
    if detector_type == "threshold":
        return ThresholdDetector(high_threshold=threshold)
    elif detector_type == "iqr":
        return IQRDetector(scale=threshold)
    return QuantileDetector(high_quantile=min(threshold, 0.999))


def _fit_and_detect(detector, scores_ts: TimeSeries) -> TimeSeries:
    """Fit detector (if needed) and return binary anomaly series."""
    if hasattr(detector, 'fit'):
        detector.fit(scores_ts)
    return detector.detect(scores_ts)


def apply_infill(
    df: pd.DataFrame, metric_cols: list[str], method: str, ts_col: str | None = None,
) -> pd.DataFrame:
    """Fill missing (NaN) values in metric columns using the specified method.

    Methods:
      - "none": do nothing
      - "linear": linear interpolation between known values
      - "time": time-weighted interpolation (uses ts_col as temporary index)
      - "ffill": forward fill (carry last known value forward)
      - "zero": fill with zeros
    """
    if method == "none":
        return df
    df = df.copy()

    if method == "time" and ts_col and ts_col in df.columns:
        # Time interpolation requires a DatetimeIndex
        orig_index = df.index
        df = df.set_index(ts_col).sort_index()
        for col in metric_cols:
            if col in df.columns:
                df[col] = df[col].interpolate(method="time", limit_direction="both")
        df = df.reset_index()
        df.index = orig_index
        return df

    for col in metric_cols:
        if col not in df.columns:
            continue
        if method == "linear":
            df[col] = df[col].interpolate(method="linear", limit_direction="both")
        elif method == "time":
            # Fallback to linear if no ts_col provided
            df[col] = df[col].interpolate(method="linear", limit_direction="both")
        elif method == "ffill":
            df[col] = df[col].ffill().bfill()
        elif method == "zero":
            df[col] = df[col].fillna(0)
        else:
            logger.warning("Unknown infill method: %s", method)
    return df


def apply_transforms(df: pd.DataFrame, metric_cols: list[str], transforms: list[str]) -> pd.DataFrame:
    """Apply data transforms to the metric columns in order.

    Supported transforms:
      - "log": log1p transform (safe for zeros)
      - "boxcox": Box-Cox power transform (positive data only, falls back to log)
      - "diff": First-order differencing
      - "scale_standard": Z-score normalization (mean=0, std=1)
      - "scale_minmax": Min-max scaling to [0, 1]
    """
    df = df.copy()
    for t in transforms:
        if t == "log":
            for col in metric_cols:
                df[col] = np.log1p(df[col].clip(lower=0))
        elif t == "boxcox":
            from scipy import stats as scipy_stats
            for col in metric_cols:
                vals = df[col].values.astype(float)
                min_val = np.nanmin(vals)
                # Box-Cox requires strictly positive values
                if min_val <= 0:
                    vals = vals - min_val + 1.0
                try:
                    transformed, _ = scipy_stats.boxcox(vals[np.isfinite(vals) & (vals > 0)])
                    # Apply the same lambda to all values
                    lam = scipy_stats.boxcox_normmax(vals[np.isfinite(vals) & (vals > 0)])
                    df[col] = scipy_stats.boxcox(vals, lmbda=lam)
                except Exception:
                    # Fall back to log if Box-Cox fails
                    df[col] = np.log1p(df[col].clip(lower=0))
        elif t == "diff":
            for col in metric_cols:
                df[col] = df[col].diff().bfill()
        elif t == "scale_standard":
            for col in metric_cols:
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    df[col] = (df[col] - mean) / std
        elif t == "scale_minmax":
            for col in metric_cols:
                mn = df[col].min()
                mx = df[col].max()
                rng = mx - mn
                if rng > 0:
                    df[col] = (df[col] - mn) / rng
        elif t == "winsorize":
            for col in metric_cols:
                vals = df[col].dropna()
                if len(vals) > 0:
                    lo = np.nanpercentile(vals, 1)
                    hi = np.nanpercentile(vals, 99)
                    df[col] = df[col].clip(lower=lo, upper=hi)
        else:
            logger.warning("Unknown transform: %s", t)
    return df


def _df_to_timeseries(df: pd.DataFrame, ts_col: str, value_cols: list[str]) -> TimeSeries:
    """Convert a DataFrame to a Darts TimeSeries with regular frequency."""
    sub = df[[ts_col] + value_cols].copy()
    sub = sub.set_index(ts_col).sort_index()

    # Drop duplicate timestamps (keep mean of duplicates)
    if sub.index.duplicated().any():
        sub = sub.groupby(sub.index).mean()

    # Infer frequency; fill gaps so Darts doesn't complain
    freq = pd.infer_freq(sub.index)
    if freq is None and len(sub) > 2:
        diffs = sub.index.to_series().diff().dropna()
        diffs = diffs[diffs > pd.Timedelta(0)]
        if len(diffs) > 0:
            median_diff = diffs.median()
            sub = sub.asfreq(median_diff)
    elif freq:
        sub = sub.asfreq(freq)

    # Fill NaN introduced by asfreq with interpolation
    sub = sub.interpolate(method="time", limit=5).ffill().bfill()

    return TimeSeries.from_dataframe(sub, value_cols=value_cols, fill_missing_dates=True)


def _classify_severity(score: float, threshold: float) -> str:
    if score > threshold * 2.0:
        return "high"
    elif score > threshold * 1.5:
        return "medium"
    return "low"


def _merge_into_regions(
    points: list[DartsAnomalyPoint],
    max_gap: int = 2,
) -> list[AnomalyRegion]:
    """Merge consecutive anomaly points into regions."""
    if not points:
        return []

    # Group by (metric, dimension_values key)
    grouped: dict[str, list[DartsAnomalyPoint]] = defaultdict(list)
    for p in points:
        dim_key = str(sorted(p.dimension_values.items())) if p.dimension_values else ""
        grouped[(p.metric, dim_key)].append(p)

    regions = []
    for (metric, dim_key), group_points in grouped.items():
        group_points.sort(key=lambda p: p.timestamp)
        current_region: list[DartsAnomalyPoint] = [group_points[0]]

        for i in range(1, len(group_points)):
            prev_ts = pd.Timestamp(current_region[-1].timestamp)
            curr_ts = pd.Timestamp(group_points[i].timestamp)
            gap = (curr_ts - prev_ts).total_seconds()
            # Use median time step * max_gap as the threshold
            median_step = 3600  # default 1 hour
            if len(group_points) > 1:
                diffs = [
                    (pd.Timestamp(group_points[j].timestamp)
                     - pd.Timestamp(group_points[j - 1].timestamp)).total_seconds()
                    for j in range(1, len(group_points))
                ]
                diffs = [d for d in diffs if d > 0]
                if diffs:
                    median_step = sorted(diffs)[len(diffs) // 2]

            if gap <= median_step * max_gap:
                current_region.append(group_points[i])
            else:
                regions.append(_region_from_points(current_region, metric))
                current_region = [group_points[i]]

        regions.append(_region_from_points(current_region, metric))

    return regions


def _region_from_points(
    points: list[DartsAnomalyPoint], metric: str,
) -> AnomalyRegion:
    scores = [p.score for p in points]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    max_sev_order = {"low": 0, "medium": 1, "high": 2}
    worst_sev = max(points, key=lambda p: max_sev_order.get(p.severity, 0)).severity
    return AnomalyRegion(
        start=points[0].timestamp,
        end=points[-1].timestamp,
        metric=metric,
        severity=worst_sev,
        avg_score=round(avg_score, 4),
        point_count=len(points),
        dimension_values=points[0].dimension_values,
    )


def _apply_volume_gate(
    anomaly_points: list[DartsAnomalyPoint],
    df_original: pd.DataFrame,
    ts_col: str,
    volume_metric: str,
    threshold: float,
) -> list[DartsAnomalyPoint]:
    """Remove anomaly points where a reference metric is below the threshold."""
    if volume_metric not in df_original.columns:
        logging.warning("Volume gate metric %r not found in data, skipping", volume_metric)
        return anomaly_points

    # Build timestamp → reference value lookup
    lookup = {}
    for _, row in df_original[[ts_col, volume_metric]].iterrows():
        ts_str = str(row[ts_col])
        val = row[volume_metric]
        if pd.notna(val):
            lookup[ts_str] = float(val)

    return [p for p in anomaly_points if lookup.get(p.timestamp, 0.0) >= threshold]


def _apply_persistence_damping(
    regions: list[AnomalyRegion],
    anomaly_points: list[DartsAnomalyPoint],
    damping: float,
    min_points: int,
    global_threshold: float,
) -> tuple[list[AnomalyRegion], list[DartsAnomalyPoint]]:
    """Filter short regions and boost severity of persistent ones."""
    # Filter out regions with too few points
    surviving = [r for r in regions if r.point_count >= min_points]

    # Build set of surviving region keys for fast lookup
    surviving_keys: set[tuple[str, str, str]] = set()
    for r in surviving:
        surviving_keys.add((r.start, r.end, r.metric))

    # Apply damping to surviving regions
    damped = []
    for r in surviving:
        if damping > 0 and r.point_count > 1:
            effective_score = r.avg_score * (1 + damping * math.log2(r.point_count))
            new_severity = _classify_severity(effective_score, global_threshold)
            damped.append(AnomalyRegion(
                start=r.start,
                end=r.end,
                metric=r.metric,
                severity=new_severity,
                avg_score=round(effective_score, 4),
                point_count=r.point_count,
                dimension_values=r.dimension_values,
            ))
        else:
            damped.append(r)

    # Remove anomaly points that belong to filtered-out regions
    if len(surviving) < len(regions):
        kept_points = []
        for p in anomaly_points:
            for r in surviving:
                if (p.metric == r.metric
                        and r.start <= p.timestamp <= r.end
                        and p.dimension_values == r.dimension_values):
                    kept_points.append(p)
                    break
        anomaly_points = kept_points

    return damped, anomaly_points


def _run_scorer_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Run a standalone scorer (KMeans, IForest, LOF, ECOD)."""
    window = max(1, int(config.params.get("window", 10)))

    # Build multivariate TimeSeries
    series = _df_to_timeseries(df, ts_col, metric_cols)
    # MPS (Apple Silicon) doesn't support float64
    if _cached_accelerator() == "mps":
        series = series.astype(np.float32)

    if progress_cb:
        progress_cb(10, "Building scorer...")

    scorer = build_scorer(config.model_id, config.params)

    if progress_cb:
        progress_cb(30, "Fitting scorer...")

    scorer.fit(series)

    if progress_cb:
        progress_cb(60, "Scoring...")

    scores_ts = scorer.score(series)

    if progress_cb:
        progress_cb(80, "Detecting anomalies...")

    detector = build_detector(config.detector_type, config.detector_threshold)
    binary_ts = _fit_and_detect(detector, scores_ts)

    # Extract results
    scores_df = scores_ts.to_dataframe()
    binary_df = binary_ts.to_dataframe()
    orig_df = series.to_dataframe()

    # Compute a threshold value for severity classification
    score_values = scores_df.values.flatten()
    score_values = score_values[~np.isnan(score_values)]
    if len(score_values) > 0:
        threshold = float(np.quantile(score_values, min(config.detector_threshold, 0.999)))
    else:
        threshold = 1.0

    for ts_idx in scores_df.index:
        ts_str = str(ts_idx)
        for i, metric in enumerate(metric_cols):
            # Score column name may differ; use positional
            score_col = scores_df.columns[min(i, len(scores_df.columns) - 1)]
            binary_col = binary_df.columns[min(i, len(binary_df.columns) - 1)]

            score_val = float(scores_df.loc[ts_idx, score_col])
            is_anom = bool(binary_df.loc[ts_idx, binary_col]) if ts_idx in binary_df.index else False

            if math.isnan(score_val):
                score_val = 0.0

            actual_val = float(orig_df.loc[ts_idx, metric]) if ts_idx in orig_df.index else 0.0
            if math.isnan(actual_val):
                actual_val = 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if is_anom:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

    # Build fitted baseline: original series with anomaly points replaced by interpolation
    if all_forecast_points is not None:
        anomaly_timestamps = {(p.timestamp, p.metric) for p in anomaly_points}
        for i, metric in enumerate(metric_cols):
            vals = orig_df[metric].copy()
            # Mask anomalous points, then interpolate to show the "normal" baseline
            for ts_idx in orig_df.index:
                ts_str = str(ts_idx)
                if (ts_str, metric) in anomaly_timestamps:
                    vals.loc[ts_idx] = np.nan
            fitted = vals.interpolate(method="linear", limit_direction="both")
            for ts_idx in orig_df.index:
                ts_str = str(ts_idx)
                actual_val = float(orig_df.loc[ts_idx, metric])
                fitted_val = float(fitted.loc[ts_idx])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str,
                        metric=metric,
                        predicted=round(fitted_val, 6),
                        actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# STL + GESD pipeline
# ---------------------------------------------------------------------------

def _gesd_test(residuals: np.ndarray, max_outliers: int, alpha: float = 0.05) -> list[int]:
    """Generalized Extreme Studentized Deviate test.

    Returns indices of detected outliers (up to *max_outliers*).
    """
    from scipy import stats as scipy_stats

    n = len(residuals)
    if n < 3 or max_outliers < 1:
        return []

    indices = list(range(n))
    data = residuals.copy()
    outlier_indices: list[int] = []

    for i in range(min(max_outliers, n - 2)):
        if len(data) < 3:
            break
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        if std < 1e-12:
            break

        # Largest deviation from mean
        deviations = np.abs(data - mean)
        max_idx = int(np.argmax(deviations))
        test_stat = deviations[max_idx] / std

        # Critical value (two-tailed t)
        p = 1.0 - alpha / (2.0 * (n - i))
        p = max(min(p, 1.0 - 1e-12), 1e-12)
        t_crit = scipy_stats.t.ppf(p, n - i - 2)
        crit = ((n - i - 1) * t_crit) / math.sqrt((n - i - 2 + t_crit ** 2) * (n - i))

        if test_stat > crit:
            outlier_indices.append(indices[max_idx])
            data = np.delete(data, max_idx)
            del indices[max_idx]
        else:
            break

    return outlier_indices


def _run_stl_gesd_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """STL decomposition + Generalized ESD outlier test on residuals."""
    from statsmodels.tsa.seasonal import STL

    period = max(2, int(config.params.get("period", 24)))
    max_anomaly_pct = float(config.params.get("max_anomaly_pct", 0.10))

    if progress_cb:
        progress_cb(5, "Preparing data...")

    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)

    # Deduplicate timestamps
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)

    work = work.set_index(ts_col)

    # Infer frequency for STL
    freq = pd.infer_freq(work.index)
    if freq is None and len(work) > 2:
        diffs = work.index.to_series().diff().dropna()
        diffs = diffs[diffs > pd.Timedelta(0)]
        if len(diffs) > 0:
            median_diff = diffs.median()
            work = work.asfreq(median_diff)
    elif freq:
        work = work.asfreq(freq)

    total_metrics = len(metric_cols)

    for m_idx, metric in enumerate(metric_cols):
        if metric not in work.columns:
            continue

        if progress_cb:
            pct = 10 + int(80 * m_idx / max(total_metrics, 1))
            progress_cb(pct, f"STL+GESD: {metric}...")

        series = work[metric].copy()
        series = series.interpolate(method="linear", limit_direction="both")
        series = series.ffill().bfill().fillna(0)
        values = series.values.astype(np.float64)

        if len(values) < period * 2:
            # Not enough data for STL — skip this metric
            logger.warning("STL+GESD: metric %s has only %d points (need %d), skipping",
                           metric, len(values), period * 2)
            continue

        # --- STL decomposition ---
        stl = STL(series, period=period, robust=True)
        result = stl.fit()
        residual = result.resid.values
        trend = result.trend.values
        seasonal = result.seasonal.values

        # --- Anomaly scores: |residual| / MAD ---
        mad = np.median(np.abs(residual - np.median(residual)))
        if mad < 1e-12:
            mad = np.std(residual) if np.std(residual) > 1e-12 else 1.0
        scores = np.abs(residual) / mad

        # --- GESD test ---
        max_outliers = max(1, int(max_anomaly_pct * len(residual)))
        outlier_idxs = set(_gesd_test(residual, max_outliers))

        # --- Threshold for severity classification ---
        valid_scores = scores[~np.isnan(scores)]
        if len(valid_scores) > 0:
            threshold = float(np.quantile(valid_scores, min(config.detector_threshold, 0.999)))
        else:
            threshold = 1.0

        # --- Populate results ---
        timestamps = series.index
        fitted_values = trend + seasonal

        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(scores[j]) if not math.isnan(scores[j]) else 0.0
            actual_val = float(values[j]) if not math.isnan(values[j]) else 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if j in outlier_idxs:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

            # Fitted baseline = trend + seasonal
            if all_forecast_points is not None:
                fitted_val = float(fitted_values[j])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str,
                        metric=metric,
                        predicted=round(fitted_val, 6),
                        actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Spectral Residual pipeline
# ---------------------------------------------------------------------------

def _spectral_residual_scores(values: np.ndarray, spectral_window: int = 3,
                              score_window: int = 21) -> np.ndarray:
    """Compute Spectral Residual saliency scores (Microsoft's SR method)."""
    n = len(values)
    if n < 3:
        return np.zeros(n)

    # FFT
    freq = np.fft.fft(values)
    amplitude = np.abs(freq)
    phase = np.angle(freq)

    # Log amplitude
    log_amp = np.log(amplitude + 1e-12)

    # Averaged log amplitude (moving average in frequency domain)
    kernel = np.ones(spectral_window) / spectral_window
    avg_log_amp = np.convolve(log_amp, kernel, mode="same")

    # Spectral residual
    spectral_res = log_amp - avg_log_amp

    # Reconstruct saliency map via inverse FFT
    saliency_freq = np.exp(spectral_res + 1j * phase)
    saliency = np.abs(np.fft.ifft(saliency_freq)) ** 2

    # Smooth saliency scores
    if score_window > 1:
        kernel2 = np.ones(score_window) / score_window
        saliency = np.convolve(saliency, kernel2, mode="same")

    return saliency


def _run_spectral_residual_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Microsoft Spectral Residual anomaly detection."""
    spectral_window = max(1, int(config.params.get("spectral_window", 3)))
    score_window = max(1, int(config.params.get("score_window", 21)))

    if progress_cb:
        progress_cb(5, "Preparing data...")

    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)

    # Deduplicate timestamps
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)

    work = work.set_index(ts_col)

    total_metrics = len(metric_cols)

    for m_idx, metric in enumerate(metric_cols):
        if metric not in work.columns:
            continue

        if progress_cb:
            pct = 10 + int(80 * m_idx / max(total_metrics, 1))
            progress_cb(pct, f"Spectral Residual: {metric}...")

        series = work[metric].copy()
        series = series.interpolate(method="linear", limit_direction="both")
        series = series.ffill().bfill().fillna(0)
        values = series.values.astype(np.float64)

        if len(values) < 3:
            continue

        # --- Compute saliency scores ---
        scores = _spectral_residual_scores(values, spectral_window, score_window)

        # --- Threshold for anomaly detection ---
        valid_scores = scores[~np.isnan(scores)]
        if len(valid_scores) > 0:
            threshold = float(np.quantile(valid_scores, min(config.detector_threshold, 0.999)))
        else:
            threshold = 1.0

        # --- Fitted baseline: reconstruct from averaged spectrum (no residual) ---
        freq = np.fft.fft(values)
        amplitude = np.abs(freq)
        phase = np.angle(freq)
        log_amp = np.log(amplitude + 1e-12)
        kernel = np.ones(spectral_window) / spectral_window
        avg_log_amp = np.convolve(log_amp, kernel, mode="same")
        baseline_freq = np.exp(avg_log_amp + 1j * phase)
        baseline = np.real(np.fft.ifft(baseline_freq))

        # --- Populate results ---
        timestamps = series.index

        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(scores[j]) if not math.isnan(scores[j]) else 0.0
            actual_val = float(values[j]) if not math.isnan(values[j]) else 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if score_val > threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

            # Fitted baseline from averaged spectrum
            if all_forecast_points is not None:
                fitted_val = float(baseline[j])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str,
                        metric=metric,
                        predicted=round(fitted_val, 6),
                        actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# CUSUM pipeline
# ---------------------------------------------------------------------------

def _run_cusum_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Cumulative Sum (CUSUM) control chart for level-shift detection."""
    drift = float(config.params.get("drift", 0.5))
    threshold_h = float(config.params.get("threshold_h", 5.0))

    if progress_cb:
        progress_cb(5, "Preparing data...")

    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    total_metrics = len(metric_cols)

    for m_idx, metric in enumerate(metric_cols):
        if metric not in work.columns:
            continue

        if progress_cb:
            pct = 10 + int(80 * m_idx / max(total_metrics, 1))
            progress_cb(pct, f"CUSUM: {metric}...")

        series = work[metric].copy()
        series = series.interpolate(method="linear", limit_direction="both")
        series = series.ffill().bfill().fillna(0)
        values = series.values.astype(np.float64)
        n = len(values)
        if n < 5:
            continue

        # Reference mean and std from the series
        mu = np.mean(values)
        sigma = np.std(values, ddof=1)
        if sigma < 1e-12:
            sigma = 1.0

        # Two-sided CUSUM
        k = drift * sigma
        h = threshold_h * sigma
        s_pos = np.zeros(n)
        s_neg = np.zeros(n)
        scores = np.zeros(n)

        for j in range(1, n):
            s_pos[j] = max(0.0, s_pos[j - 1] + (values[j] - mu) - k)
            s_neg[j] = max(0.0, s_neg[j - 1] - (values[j] - mu) - k)
            scores[j] = max(s_pos[j], s_neg[j])

        # Normalize scores by h for severity
        norm_scores = scores / max(h, 1e-12)

        # Threshold for severity
        valid_scores = norm_scores[norm_scores > 0]
        if len(valid_scores) > 0:
            threshold = float(np.quantile(norm_scores[~np.isnan(norm_scores)],
                                          min(config.detector_threshold, 0.999)))
        else:
            threshold = 1.0

        timestamps = series.index
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(norm_scores[j])
            actual_val = float(values[j]) if not math.isnan(values[j]) else 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if scores[j] > h:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

            # Baseline = reference mean
            if all_forecast_points is not None:
                all_forecast_points.append(ForecastPoint(
                    timestamp=ts_str,
                    metric=metric,
                    predicted=round(float(mu), 6),
                    actual=round(actual_val, 6),
                ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Hampel filter pipeline
# ---------------------------------------------------------------------------

def _run_hampel_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Hampel filter — sliding-window median-based outlier detection."""
    half_window = max(1, int(config.params.get("window", 11)) // 2)
    n_sigma = float(config.params.get("n_sigma", 3.0))
    # Scale factor: MAD to std for normal distribution
    k_mad = 1.4826

    if progress_cb:
        progress_cb(5, "Preparing data...")

    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    total_metrics = len(metric_cols)

    for m_idx, metric in enumerate(metric_cols):
        if metric not in work.columns:
            continue

        if progress_cb:
            pct = 10 + int(80 * m_idx / max(total_metrics, 1))
            progress_cb(pct, f"Hampel: {metric}...")

        series = work[metric].copy()
        series = series.interpolate(method="linear", limit_direction="both")
        series = series.ffill().bfill().fillna(0)
        values = series.values.astype(np.float64)
        n = len(values)
        if n < 3:
            continue

        medians = np.zeros(n)
        mad_values = np.zeros(n)
        scores = np.zeros(n)

        for j in range(n):
            lo = max(0, j - half_window)
            hi = min(n, j + half_window + 1)
            window_data = values[lo:hi]
            med = np.median(window_data)
            mad = np.median(np.abs(window_data - med))
            medians[j] = med
            mad_values[j] = mad
            sigma_est = k_mad * mad if mad > 1e-12 else 1e-12
            scores[j] = abs(values[j] - med) / sigma_est

        # Threshold for severity classification
        valid_scores = scores[~np.isnan(scores)]
        if len(valid_scores) > 0:
            threshold = float(np.quantile(valid_scores,
                                          min(config.detector_threshold, 0.999)))
        else:
            threshold = 1.0

        timestamps = series.index
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(scores[j])
            actual_val = float(values[j]) if not math.isnan(values[j]) else 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if score_val > n_sigma:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

            # Fitted baseline = local median
            if all_forecast_points is not None:
                fitted_val = float(medians[j])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str,
                        metric=metric,
                        predicted=round(fitted_val, 6),
                        actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Change Point Detection pipeline (ruptures)
# ---------------------------------------------------------------------------

def _run_changepoint_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Change point detection using PELT algorithm from ruptures."""
    import ruptures as rpt

    cost_model = str(config.params.get("model", "rbf"))
    penalty = float(config.params.get("penalty", 3.0))

    if progress_cb:
        progress_cb(5, "Preparing data...")

    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    total_metrics = len(metric_cols)

    for m_idx, metric in enumerate(metric_cols):
        if metric not in work.columns:
            continue

        if progress_cb:
            pct = 10 + int(80 * m_idx / max(total_metrics, 1))
            progress_cb(pct, f"Change points: {metric}...")

        series = work[metric].copy()
        series = series.interpolate(method="linear", limit_direction="both")
        series = series.ffill().bfill().fillna(0)
        values = series.values.astype(np.float64)
        n = len(values)
        if n < 5:
            continue

        # Run PELT
        # Penalty is scaled by log(n) * user_penalty to be more intuitive
        pen = penalty * np.log(n)
        algo = rpt.Pelt(model=cost_model, min_size=2, jump=1).fit(values)
        change_points = algo.predict(pen=pen)
        # ruptures returns breakpoint indices (1-based end of segments), last is always n
        cp_set = set(change_points[:-1]) if change_points else set()

        # Build piecewise-constant baseline (segment means)
        baseline = np.zeros(n)
        prev = 0
        segment_boundaries = sorted(cp_set | {n})
        for bp in segment_boundaries:
            seg_mean = np.mean(values[prev:bp])
            baseline[prev:bp] = seg_mean
            prev = bp

        # Score = distance from local segment mean, normalized by global std
        global_std = np.std(values, ddof=1)
        if global_std < 1e-12:
            global_std = 1.0

        scores = np.abs(values - baseline) / global_std

        # Points near change points get boosted scores
        cp_list = sorted(cp_set)
        for cp_idx in cp_list:
            # Score the change point and its immediate neighbours
            for offset in range(-2, 3):
                j = cp_idx + offset
                if 0 <= j < n:
                    # Boost: difference between segment means at this boundary
                    left_end = max(0, cp_idx - 1)
                    right_start = min(cp_idx, n - 1)
                    left_mean = np.mean(values[max(0, left_end - 5):cp_idx])
                    right_mean = np.mean(values[cp_idx:min(n, right_start + 6)])
                    jump_score = abs(right_mean - left_mean) / global_std
                    scores[j] = max(scores[j], jump_score)

        # Threshold for severity
        valid_scores = scores[~np.isnan(scores)]
        if len(valid_scores) > 0:
            threshold = float(np.quantile(valid_scores,
                                          min(config.detector_threshold, 0.999)))
        else:
            threshold = 1.0

        timestamps = series.index
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(scores[j]) if not math.isnan(scores[j]) else 0.0
            actual_val = float(values[j]) if not math.isnan(values[j]) else 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if score_val > threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

            # Fitted baseline = piecewise segment mean
            if all_forecast_points is not None:
                fitted_val = float(baseline[j])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str,
                        metric=metric,
                        predicted=round(fitted_val, 6),
                        actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Modified Z-Score pipeline
# ---------------------------------------------------------------------------

def _run_modified_zscore_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Modified Z-Score: 0.6745 * |x - median| / MAD."""
    zscore_threshold = float(config.params.get("threshold", 3.5))

    if progress_cb:
        progress_cb(5, "Preparing data...")

    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    total_metrics = len(metric_cols)

    for m_idx, metric in enumerate(metric_cols):
        if metric not in work.columns:
            continue

        if progress_cb:
            pct = 10 + int(80 * m_idx / max(total_metrics, 1))
            progress_cb(pct, f"Modified Z-Score: {metric}...")

        series = work[metric].copy()
        series = series.interpolate(method="linear", limit_direction="both")
        series = series.ffill().bfill().fillna(0)
        values = series.values.astype(np.float64)
        n = len(values)
        if n < 3:
            continue

        median = np.median(values)
        mad = np.median(np.abs(values - median))
        if mad < 1e-12:
            mad = np.std(values) if np.std(values) > 1e-12 else 1.0

        scores = 0.6745 * np.abs(values - median) / mad

        # Threshold for severity classification
        valid_scores = scores[~np.isnan(scores)]
        if len(valid_scores) > 0:
            threshold = float(np.quantile(valid_scores,
                                          min(config.detector_threshold, 0.999)))
        else:
            threshold = 1.0

        timestamps = series.index
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(scores[j]) if not math.isnan(scores[j]) else 0.0
            actual_val = float(values[j]) if not math.isnan(values[j]) else 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if score_val > zscore_threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

            # Baseline = median
            if all_forecast_points is not None:
                all_forecast_points.append(ForecastPoint(
                    timestamp=ts_str,
                    metric=metric,
                    predicted=round(float(median), 6),
                    actual=round(actual_val, 6),
                ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# TSPulse foundation model pipeline (IBM Granite)
# ---------------------------------------------------------------------------

_tspulse_model_cache: dict[int, object] = {}


def _get_tspulse_model(num_channels: int):
    """Get or create a cached TSPulse model for the given channel count."""
    if num_channels not in _tspulse_model_cache:
        from tsfm_public.models.tspulse.modeling_tspulse import (
            TSPulseForReconstruction,
        )
        _tspulse_model_cache[num_channels] = (
            TSPulseForReconstruction.from_pretrained(
                "ibm-granite/granite-timeseries-tspulse-r1",
                num_input_channels=num_channels,
                revision="main",
                mask_type="user",
            )
        )
    return _tspulse_model_cache[num_channels]


def _run_tspulse_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Run IBM TSPulse foundation model for anomaly detection.

    TSPulse operates directly on pandas DataFrames (no Darts TimeSeries).
    It combines time-domain and frequency-domain reconstruction to produce
    anomaly scores normalized to [0, 1].
    """
    try:
        from tsfm_public.toolkit.time_series_anomaly_detection_pipeline import (
            TimeSeriesAnomalyDetectionPipeline,
        )
    except ImportError:
        raise ImportError(
            "TSPulse requires 'granite-tsfm'. "
            "Install with: pip install 'darts-anomaly-demo[torch]'"
        )

    if progress_cb:
        progress_cb(5, "Loading TSPulse model (first run downloads weights)...")

    num_channels = len(metric_cols)
    model = _get_tspulse_model(num_channels)

    # --- Parse user params ---
    scoring_mode_str = str(config.params.get("scoring_mode", "time+fft"))
    mode_map = {
        "time+fft": ["time", "fft"],
        "time": ["time"],
        "fft": ["fft"],
    }
    prediction_mode = mode_map.get(scoring_mode_str, ["time", "fft"])

    aggregation_length = int(config.params.get("aggregation_length", 64))
    smoothing_length = int(config.params.get("smoothing_length", 8))

    if progress_cb:
        progress_cb(15, "Preparing data...")

    # --- Prepare input DataFrame ---
    # When dimensions are selected the df has multiple rows per timestamp
    # (one per node/entity).  TSPulse needs a single time series with
    # unique timestamps, so we collapse by averaging.  We then construct a
    # brand-new DataFrame so no stale index from the dimensional data leaks
    # into the granite-tsfm pipeline (which assigns scores back by index).
    tsp_df = df[[ts_col] + metric_cols].copy()
    tsp_df[ts_col] = pd.to_datetime(tsp_df[ts_col], errors="coerce")
    tsp_df = tsp_df.dropna(subset=[ts_col])

    # Collapse duplicate timestamps (from dimension grouping)
    if tsp_df[ts_col].duplicated().any():
        tsp_df = tsp_df.groupby(ts_col, as_index=False)[metric_cols].mean()

    tsp_df = tsp_df.sort_values(ts_col)

    # Interpolate NaN in metric columns
    for col in metric_cols:
        tsp_df[col] = tsp_df[col].interpolate(method="linear", limit_direction="both")
        tsp_df[col] = tsp_df[col].ffill().bfill().fillna(0)

    # Build a fresh DataFrame with a clean RangeIndex so the granite-tsfm
    # pipeline doesn't inherit a stale index from the pre-groupby data.
    tsp_df = pd.DataFrame(
        {ts_col: tsp_df[ts_col].values, **{c: tsp_df[c].values for c in metric_cols}},
    )

    if progress_cb:
        progress_cb(25, "Creating TSPulse pipeline...")

    pipeline = TimeSeriesAnomalyDetectionPipeline(
        model,
        timestamp_column=ts_col,
        target_columns=metric_cols,
        prediction_mode=prediction_mode,
        aggregation_length=aggregation_length,
        aggr_function="max",
        smoothing_length=smoothing_length,
        least_significant_scale=0.01,
        least_significant_score=0.1,
    )

    if progress_cb:
        progress_cb(35, "Running TSPulse inference...")

    result_df = pipeline(tsp_df, batch_size=256)

    if progress_cb:
        progress_cb(75, "Processing results...")

    # --- Extract scores ---
    score_col = "anomaly_score"
    if score_col not in result_df.columns:
        logger.error("TSPulse output missing 'anomaly_score'. Columns: %s",
                     list(result_df.columns))
        return

    score_values = result_df[score_col].values.astype(float)
    score_values = np.where(np.isfinite(score_values), score_values, 0.0)
    timestamps = result_df[ts_col].values

    # --- Binary detection using existing detector infrastructure ---
    score_series_df = pd.DataFrame(
        {"score": score_values},
        index=pd.DatetimeIndex(timestamps),
    )
    if score_series_df.index.duplicated().any():
        score_series_df = score_series_df[~score_series_df.index.duplicated(keep="first")]

    scores_ts = TimeSeries.from_dataframe(
        score_series_df, value_cols=["score"], fill_missing_dates=True,
    )

    detector = build_detector(config.detector_type, config.detector_threshold)
    binary_ts = _fit_and_detect(detector, scores_ts)
    binary_df = binary_ts.to_dataframe()

    # Severity threshold from positive scores
    positive_scores = score_values[score_values > 0]
    threshold = (
        float(np.quantile(positive_scores, min(config.detector_threshold, 0.999)))
        if len(positive_scores) > 0
        else 0.5
    )

    if progress_cb:
        progress_cb(85, "Building results...")

    # --- Emit scores and anomaly points ---
    for i in range(len(result_df)):
        ts_val = pd.Timestamp(timestamps[i])
        ts_str = str(ts_val)
        score_val = float(score_values[i])

        for metric in metric_cols:
            actual_val = float(result_df[metric].iloc[i])
            if not math.isfinite(actual_val):
                actual_val = 0.0

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            is_anom = (
                bool(binary_df.iloc[binary_df.index.get_indexer([ts_val], method="nearest")[0], 0])
                if len(binary_df) > 0
                else False
            )
            if is_anom:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str,
                    metric=metric,
                    value=round(actual_val, 6),
                    score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

    # TSPulse is a scorer, not a forecast model — no predicted baseline to show.
    # Emitting forecast points would produce misleading linear interpolation lines.

    if progress_cb:
        progress_cb(100, "Done")


def _run_forecast_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint],
    progress_cb: Callable | None = None,
):
    """Run a forecast-based anomaly model (per metric, univariate).

    Uses a sliding-window train/predict approach: fits on a training window,
    predicts the next chunk, slides forward. Much faster than historical_forecasts
    which retrains at every single step.
    """
    total_metrics = len(metric_cols)

    for m_idx, metric in enumerate(metric_cols):
        pct_base = (m_idx / total_metrics) * 100

        if progress_cb:
            progress_cb(pct_base + 5, f"Processing {metric}...")

        series = _df_to_timeseries(df, ts_col, [metric])
        # MPS (Apple Silicon) doesn't support float64
        if _cached_accelerator() == "mps":
            series = series.astype(np.float32)
        n = len(series)
        forecast_model = build_forecast_model(config.model_id, config.params)
        min_train = max(forecast_model.min_train_series_length, 10)

        if progress_cb:
            progress_cb(pct_base + 15, f"Forecasting {metric}...")

        # Sliding window: train on [0..i), predict chunk of `stride` points
        # Use larger strides so we don't refit thousands of times
        stride = max(1, n // 20)  # ~20 refits total
        train_start = max(int(n * 0.3), min_train + 1)

        all_pred_vals = np.full(n, np.nan)
        steps_done = 0
        total_steps = max(1, (n - train_start) // stride + 1)

        i = train_start
        while i < n:
            horizon = min(stride, n - i)
            try:
                model = build_forecast_model(config.model_id, config.params)
                model.fit(series[:i])
                pred = model.predict(horizon)
                pred_values = pred.to_dataframe().iloc[:, 0].values.astype(float)
                all_pred_vals[i:i + len(pred_values)] = pred_values
            except Exception as e:
                logger.warning("Forecast chunk failed at %d for %s: %s", i, metric, e)
            i += stride
            steps_done += 1
            if progress_cb:
                frac = min(steps_done / total_steps, 1.0)
                progress_cb(pct_base + 15 + frac * 55, f"Forecasting {metric}...")

        if progress_cb:
            progress_cb(pct_base + 75, f"Scoring {metric}...")

        orig_df = series.to_dataframe()
        actual_vals = orig_df.iloc[:, 0].values.astype(float)

        # Determine predicted region
        has_pred = np.isfinite(all_pred_vals)
        if not has_pred.any():
            logger.warning("No predictions produced for %s", metric)
            continue

        first_pred = int(np.argmax(has_pred))
        score_index = orig_df.index[first_pred:]

        # --- Scoring: use Darts scorer (DifferenceScorer is the default) ---
        scorer_id = getattr(config, "scorer_id", "difference")
        scorer = build_residual_scorer(scorer_id, config.params)

        actual_region = actual_vals[first_pred:].copy()
        pred_region = all_pred_vals[first_pred:].copy()
        # Fill prediction gaps so scorer gets continuous series
        gap_mask = ~np.isfinite(pred_region)
        pred_region[gap_mask] = actual_region[gap_mask]

        actual_sub_df = pd.DataFrame({metric: actual_region}, index=score_index)
        pred_sub_df = pd.DataFrame({metric: pred_region}, index=score_index)
        actual_ts_sub = TimeSeries.from_dataframe(actual_sub_df, fill_missing_dates=True)
        pred_ts_sub = TimeSeries.from_dataframe(pred_sub_df, fill_missing_dates=True)

        if scorer_id not in ("difference", "norm"):
            scorer.fit_from_prediction(actual_ts_sub, pred_ts_sub)

        scores_ts = scorer.score_from_prediction(actual_ts_sub, pred_ts_sub)

        if progress_cb:
            progress_cb(pct_base + 85, f"Detecting {metric}...")

        detector = build_detector(config.detector_type, config.detector_threshold)
        binary_ts = _fit_and_detect(detector, scores_ts)
        scores_df = scores_ts.to_dataframe()
        binary_df = binary_ts.to_dataframe()

        # Severity threshold from score distribution
        score_arr = scores_df.values.flatten()
        finite_scores = score_arr[np.isfinite(score_arr) & (score_arr > 0)]
        threshold = float(np.quantile(finite_scores, min(config.detector_threshold, 0.999))) if len(finite_scores) > 0 else 1.0

        # Collect forecast points and scores
        for i in range(n):
            ts_idx = orig_df.index[i]
            ts_str = str(ts_idx)
            a_val = float(actual_vals[i]) if math.isfinite(actual_vals[i]) else 0.0

            if has_pred[i]:
                p_val = float(all_pred_vals[i])
                if math.isfinite(p_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str,
                        metric=metric,
                        predicted=round(p_val, 6),
                        actual=round(a_val, 6),
                    ))

            if ts_idx in scores_df.index:
                score_val = float(scores_df.loc[ts_idx].iloc[0])
                if math.isnan(score_val):
                    score_val = 0.0

                all_scores.append({
                    "timestamp": ts_str,
                    "metric": metric,
                    "score": round(score_val, 6),
                })

                is_anom = (
                    bool(binary_df.loc[ts_idx].iloc[0])
                    if ts_idx in binary_df.index
                    else False
                )
                if is_anom:
                    anomaly_points.append(DartsAnomalyPoint(
                        timestamp=ts_str,
                        metric=metric,
                        value=round(a_val, 6),
                        score=round(score_val, 6),
                        is_anomaly=True,
                        severity=_classify_severity(score_val, threshold),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


def _run_global_forecast_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint],
    progress_cb: Callable | None = None,
):
    """Run a global forecasting model (LinearRegression, RandomForest).

    Global models support multivariate data and can be fit once then predict
    without retraining, making historical_forecasts very fast.
    """
    series = _df_to_timeseries(df, ts_col, metric_cols)

    # MPS (Apple Silicon) doesn't support float64 — cast to float32
    if _cached_accelerator() == "mps":
        series = series.astype(np.float32)

    n = len(series)

    is_foundation = config.model_id in FOUNDATION_MODELS

    # Foundation models are huge (120-200M params) running on CPU.
    # Cap the series length to keep inference tractable.
    MAX_FOUNDATION_POINTS = 3000
    if is_foundation and n > MAX_FOUNDATION_POINTS:
        # ceil division ensures step >= 2 when n > MAX
        step = -(-n // MAX_FOUNDATION_POINTS)  # ceil(n / MAX)
        logger.info(
            "Downsampling series from %d to ~%d points (step=%d) for foundation model",
            n, n // step, step,
        )
        if progress_cb:
            progress_cb(5, f"Downsampling {n:,} to ~{n // step:,} points for speed...")
        series = series[::step]
        n = len(series)

    if progress_cb:
        if is_foundation:
            progress_cb(8, "Loading pre-trained model (first run downloads weights)...")
        else:
            progress_cb(10, "Fitting model...")

    model = build_global_forecast_model(config.model_id, config.params)

    lags = int(config.params.get("lags", config.params.get("input_chunk_length", 24)))
    min_train = max(lags + 1, 30)
    train_start = max(int(n * 0.3), min_train + 1)

    if train_start >= n - 1:
        logger.warning("Not enough data for global forecast model")
        return

    if progress_cb:
        progress_cb(15, "Model loaded, fitting...")

    model.fit(series[:train_start])

    forecast_points = n - train_start
    if is_foundation:
        num_passes = max(1, forecast_points // FOUNDATION_CHUNK_SIZE)
        if progress_cb:
            progress_cb(40, f"Generating forecasts ({num_passes} passes over {forecast_points:,} points)...")
    elif progress_cb:
        progress_cb(40, "Generating forecasts...")

    try:
        if is_foundation:
            # Foundation models: predict FOUNDATION_CHUNK_SIZE steps per forward
            # pass to avoid one-pass-per-timestep bottleneck.
            fh = FOUNDATION_CHUNK_SIZE
            forecasts_list = model.historical_forecasts(
                series,
                start=train_start,
                forecast_horizon=fh,
                stride=fh,
                retrain=False,
                last_points_only=False,
                verbose=False,
            )
            # historical_forecasts with last_points_only=False returns a list
            # of TimeSeries (one per window). Concatenate into a single series.
            if isinstance(forecasts_list, list) and len(forecasts_list) > 0:
                combined = forecasts_list[0]
                for ts_chunk in forecasts_list[1:]:
                    combined = combined.append(ts_chunk)
                forecasts = combined
            else:
                forecasts = forecasts_list
        else:
            forecasts = model.historical_forecasts(
                series,
                start=train_start,
                forecast_horizon=1,
                stride=1,
                retrain=False,
                last_points_only=True,
                verbose=False,
            )
    except Exception as e:
        logger.error("historical_forecasts failed: %s", e)
        return

    if progress_cb:
        progress_cb(70, "Computing scores...")

    pred_df = forecasts.to_dataframe()
    orig_df = series.to_dataframe()
    common_idx = pred_df.index.intersection(orig_df.index)

    if len(common_idx) == 0:
        logger.warning("No overlapping predictions for global model")
        return

    scorer_id = getattr(config, "scorer_id", "difference")

    for m_idx, metric in enumerate(metric_cols):
        orig_col = orig_df.columns[m_idx]
        pred_col = pred_df.columns[min(m_idx, len(pred_df.columns) - 1)]

        actuals = orig_df.loc[common_idx, orig_col].values.astype(float)
        preds = pred_df.loc[common_idx, pred_col].values.astype(float)

        # --- Scoring: use Darts scorer (DifferenceScorer is the default) ---
        scorer = build_residual_scorer(scorer_id, config.params)

        actual_sub_df = pd.DataFrame({metric: actuals}, index=common_idx)
        pred_sub_df = pd.DataFrame({metric: preds}, index=common_idx)
        actual_ts_sub = TimeSeries.from_dataframe(actual_sub_df, fill_missing_dates=True)
        pred_ts_sub = TimeSeries.from_dataframe(pred_sub_df, fill_missing_dates=True)

        if scorer_id not in ("difference", "norm"):
            scorer.fit_from_prediction(actual_ts_sub, pred_ts_sub)

        scores_ts = scorer.score_from_prediction(actual_ts_sub, pred_ts_sub)

        if progress_cb:
            progress_cb(75 + m_idx * 20 // len(metric_cols), f"Detecting {metric}...")

        detector = build_detector(config.detector_type, config.detector_threshold)
        binary_ts = _fit_and_detect(detector, scores_ts)
        scores_df_result = scores_ts.to_dataframe()
        binary_df = binary_ts.to_dataframe()

        score_arr = scores_df_result.values.flatten()
        finite_scores = score_arr[np.isfinite(score_arr) & (score_arr > 0)]
        threshold = (
            float(np.quantile(finite_scores, min(config.detector_threshold, 0.999)))
            if len(finite_scores) > 0
            else 1.0
        )

        for i, ts_idx in enumerate(common_idx):
            ts_str = str(ts_idx)
            a_val = float(actuals[i]) if np.isfinite(actuals[i]) else 0.0
            p_val = float(preds[i]) if np.isfinite(preds[i]) else 0.0

            all_forecast_points.append(ForecastPoint(
                timestamp=ts_str, metric=metric,
                predicted=round(p_val, 6), actual=round(a_val, 6),
            ))

            if ts_idx in scores_df_result.index:
                score_val = float(scores_df_result.loc[ts_idx].iloc[0])
                if math.isnan(score_val):
                    score_val = 0.0
            else:
                score_val = 0.0

            all_scores.append({
                "timestamp": ts_str, "metric": metric,
                "score": round(score_val, 6),
            })

            is_anom = (
                bool(binary_df.loc[ts_idx].iloc[0])
                if ts_idx in binary_df.index
                else False
            )
            if is_anom:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str, metric=metric,
                    value=round(a_val, 6), score=round(score_val, 6),
                    is_anomaly=True,
                    severity=_classify_severity(score_val, threshold),
                ))

    if progress_cb:
        progress_cb(100, "Done")


def _run_peer_divergence_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Compare each dimension group against the peer consensus.

    Groups the data by the first selected dimension (e.g. NODE_NAME), computes
    a consensus time series (median or mean of all peers), then scores each
    group by its deviation from the consensus.

    Normalization modes (param "normalization"):
      - "mad"   : MAD-normalized score (how many MADs away from consensus)
      - "pct"   : percentage deviation from consensus (|actual-consensus|/consensus*100)
      - "zscore": modified z-score using cohort std deviation

    Detection uses a GLOBAL threshold across all nodes so consistently
    divergent nodes are properly flagged.
    """
    dim_cols = list(config.dimensions) if config.dimensions else []
    if not dim_cols:
        raise ValueError("Peer Divergence requires at least one dimension selected")

    dim_col = dim_cols[0]  # group by first dimension
    if dim_col not in df.columns:
        raise ValueError(f"Dimension column '{dim_col}' not found in data")

    method = str(config.params.get("method", "median"))
    min_peers = int(config.params.get("min_peers", 3))
    normalization = str(config.params.get("normalization", "pct"))

    groups = df[dim_col].unique()
    if len(groups) < min_peers:
        raise ValueError(
            f"Need at least {min_peers} peer groups, but only found {len(groups)}"
        )

    if progress_cb:
        progress_cb(5, "Building peer groups...")

    # Build per-group time series: {group_name: DataFrame indexed by timestamp}
    # Also track which timestamps have ACTUAL data per group (for straight-line fix)
    peer_data: dict[str, pd.DataFrame] = {}
    actual_timestamps: dict[str, set] = {}
    for group_name in groups:
        gdf = df[df[dim_col] == group_name].copy()
        gdf = gdf.set_index(ts_col).sort_index()
        # Keep only metric columns, drop duplicates
        gdf = gdf[metric_cols]
        if gdf.index.duplicated().any():
            gdf = gdf.groupby(gdf.index).mean()
        actual_timestamps[group_name] = set(gdf.index)
        peer_data[group_name] = gdf

    if progress_cb:
        progress_cb(15, "Computing consensus...")

    # Build consensus: align all peers to a common time index
    all_indices = sorted(set().union(*(g.index for g in peer_data.values())))
    common_idx = pd.DatetimeIndex(all_indices)

    # Stack all peer values into a 3D array: (time, metrics, peers)
    aligned: dict[str, pd.DataFrame] = {}
    for gname, gdf in peer_data.items():
        reindexed = gdf.reindex(common_idx)
        reindexed = reindexed.interpolate(method="time", limit=3).ffill().bfill()
        aligned[gname] = reindexed

    # Consensus: median or mean across peers at each timestamp
    stacked = np.stack([aligned[g].values for g in aligned], axis=-1)  # (T, M, P)
    if method == "mean":
        consensus = np.nanmean(stacked, axis=-1)  # (T, M)
    else:
        consensus = np.nanmedian(stacked, axis=-1)  # (T, M)

    consensus_df = pd.DataFrame(consensus, index=common_idx, columns=metric_cols)

    # Emit consensus as "forecast" so the chart shows the peer norm
    if all_forecast_points is not None:
        for m_idx, metric in enumerate(metric_cols):
            for ts_idx in common_idx:
                c_val = float(consensus_df.loc[ts_idx, metric])
                if math.isfinite(c_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=str(ts_idx),
                        metric=metric,
                        predicted=round(c_val, 6),
                        actual=round(c_val, 6),  # consensus is the reference
                    ))

    if progress_cb:
        progress_cb(30, "Scoring divergence...")

    # Pre-compute normalization denominators
    if normalization == "pct":
        # Percentage deviation: |actual - consensus| / max(|consensus|, eps) * 100
        eps = np.nanmax(np.abs(consensus)) * 1e-6 if np.nanmax(np.abs(consensus)) > 0 else 1.0
        consensus_safe = np.where(np.abs(consensus) > eps, np.abs(consensus), eps)
    elif normalization == "zscore":
        # Modified z-score: deviation / std across peers
        peer_std = np.nanstd(stacked, axis=-1)  # (T, M)
        std_safe = np.where(peer_std > 0, peer_std, 1.0)
    else:
        # MAD normalization (original)
        deviations_from_median = np.abs(stacked - consensus[:, :, np.newaxis])  # (T, M, P)
        mad = np.nanmedian(deviations_from_median, axis=-1)  # (T, M)
        mad_safe = np.where(mad > 0, mad, 1.0)

    # --- Phase 1: Compute scores for ALL nodes, collect globally ---
    all_node_scores: dict[str, dict[str, np.ndarray]] = {}  # {group: {metric: scores}}
    all_node_masks: dict[str, np.ndarray] = {}  # {group: bool mask of actual timestamps}

    group_names_ordered = list(aligned.keys())
    for g_idx, group_name in enumerate(group_names_ordered):
        gdf = aligned[group_name]
        deviation = np.abs(gdf.values - consensus_df.values)  # (T, M)

        # Normalize based on selected method
        if normalization == "pct":
            norm_scores = (deviation / consensus_safe) * 100.0
        elif normalization == "zscore":
            norm_scores = deviation / std_safe
        else:
            norm_scores = deviation / mad_safe

        # Build mask: True where this group has actual (non-interpolated) data
        actual_set = actual_timestamps[group_name]
        mask = np.array([ts in actual_set for ts in common_idx])
        all_node_masks[group_name] = mask

        metric_score_dict = {}
        for m_idx, metric in enumerate(metric_cols):
            scores = norm_scores[:, m_idx].copy()
            scores = np.where(np.isfinite(scores), scores, 0.0)
            # Zero out scores at interpolated timestamps
            scores[~mask] = 0.0
            metric_score_dict[metric] = scores

        all_node_scores[group_name] = metric_score_dict

    if progress_cb:
        progress_cb(50, "Computing global threshold...")

    # --- Phase 2: Build GLOBAL threshold per metric ---
    # Collect all scores from all nodes (only at actual data points) to fit one detector
    global_thresholds: dict[str, float] = {}
    for metric in metric_cols:
        all_metric_scores = []
        for group_name in group_names_ordered:
            mask = all_node_masks[group_name]
            scores = all_node_scores[group_name][metric]
            all_metric_scores.append(scores[mask])
        combined = np.concatenate(all_metric_scores)
        finite = combined[combined > 0]
        if len(finite) > 0:
            global_thresholds[metric] = float(
                np.quantile(finite, min(config.detector_threshold, 0.999))
            )
        else:
            global_thresholds[metric] = 1.0

    if progress_cb:
        progress_cb(60, "Detecting anomalies...")

    # --- Phase 3: Emit scores and anomalies using global threshold ---
    total_groups = len(group_names_ordered)
    for g_idx, group_name in enumerate(group_names_ordered):
        if progress_cb:
            pct = 60 + (g_idx / total_groups) * 35
            progress_cb(pct, f"Scoring {group_name}...")

        gdf = aligned[group_name]
        mask = all_node_masks[group_name]
        dim_values = {dim_col: str(group_name)}

        for m_idx, metric in enumerate(metric_cols):
            metric_scores = all_node_scores[group_name][metric]
            threshold = global_thresholds[metric]

            for t_idx, ts_idx in enumerate(common_idx):
                # Only emit scores at timestamps where this node had actual data
                if not mask[t_idx]:
                    continue

                ts_str = str(ts_idx)
                score_val = round(float(metric_scores[t_idx]), 6)
                actual_val = float(gdf.iloc[t_idx, m_idx])
                if not math.isfinite(actual_val):
                    actual_val = 0.0

                all_scores.append({
                    "timestamp": ts_str,
                    "metric": metric,
                    "score": score_val,
                    "dimension_values": dim_values,
                })

                # Anomaly if score exceeds global threshold
                is_anom = score_val > threshold
                if is_anom:
                    anomaly_points.append(DartsAnomalyPoint(
                        timestamp=ts_str,
                        metric=metric,
                        value=round(actual_val, 6),
                        score=score_val,
                        is_anomaly=True,
                        severity=_classify_severity(score_val, threshold),
                        dimension_values=dim_values,
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Shared peer group preparation helper
# ---------------------------------------------------------------------------

def _prepare_peer_groups(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    progress_cb: Callable | None = None,
) -> tuple[
    str,                           # dim_col
    pd.DatetimeIndex,              # common_idx
    dict[str, pd.DataFrame],      # aligned (interpolated, on common_idx)
    dict[str, set],                # actual_timestamps per group
    dict[str, pd.DataFrame],      # peer_data (original, own index)
]:
    """Common setup for all peer analysis pipelines.

    Returns the dimension column name, common time index, aligned DataFrames,
    actual-timestamp sets, and the raw per-group DataFrames.
    """
    dim_cols = list(config.dimensions) if config.dimensions else []
    if not dim_cols:
        raise ValueError("This model requires at least one dimension selected")
    dim_col = dim_cols[0]
    if dim_col not in df.columns:
        raise ValueError(f"Dimension column '{dim_col}' not found in data")

    min_peers = int(config.params.get("min_peers", 3))
    groups = df[dim_col].unique()
    if len(groups) < min_peers:
        raise ValueError(
            f"Need at least {min_peers} peer groups, but only found {len(groups)}"
        )

    if progress_cb:
        progress_cb(5, "Building peer groups...")

    peer_data: dict[str, pd.DataFrame] = {}
    actual_timestamps: dict[str, set] = {}
    for group_name in groups:
        gdf = df[df[dim_col] == group_name].copy()
        gdf = gdf.set_index(ts_col).sort_index()
        gdf = gdf[metric_cols]
        if gdf.index.duplicated().any():
            gdf = gdf.groupby(gdf.index).mean()
        actual_timestamps[group_name] = set(gdf.index)
        peer_data[group_name] = gdf

    all_indices = sorted(set().union(*(g.index for g in peer_data.values())))
    common_idx = pd.DatetimeIndex(all_indices)

    aligned: dict[str, pd.DataFrame] = {}
    for gname, gdf in peer_data.items():
        reindexed = gdf.reindex(common_idx)
        reindexed = reindexed.interpolate(method="time", limit=3).ffill().bfill()
        aligned[gname] = reindexed

    return dim_col, common_idx, aligned, actual_timestamps, peer_data


def _emit_peer_scores_and_anomalies(
    group_names: list[str],
    metric_cols: list[str],
    common_idx: pd.DatetimeIndex,
    aligned: dict[str, pd.DataFrame],
    actual_timestamps: dict[str, set],
    score_matrix: dict[str, np.ndarray],   # {group_name: (T, M) scores}
    dim_col: str,
    config: DartsDetectionConfig,
    anomaly_points: list,
    all_scores: list[dict],
    progress_cb: Callable | None = None,
    progress_start: float = 60,
    progress_end: float = 95,
):
    """Shared emitter: compute global thresholds and emit scores/anomalies.

    score_matrix maps each group name to a (T, M) array of scores. Scores at
    interpolated timestamps are zeroed and skipped in output.
    """
    # Zero out scores at interpolated timestamps
    for group_name in group_names:
        actual_set = actual_timestamps[group_name]
        mask = np.array([ts in actual_set for ts in common_idx])
        score_matrix[group_name][~mask] = 0.0

    # Global threshold per metric
    global_thresholds: dict[str, float] = {}
    for m_idx, metric in enumerate(metric_cols):
        all_metric_scores = []
        for group_name in group_names:
            actual_set = actual_timestamps[group_name]
            mask = np.array([ts in actual_set for ts in common_idx])
            scores = score_matrix[group_name][:, m_idx]
            all_metric_scores.append(scores[mask])
        combined = np.concatenate(all_metric_scores)
        finite = combined[combined > 0]
        if len(finite) > 0:
            global_thresholds[metric] = float(
                np.quantile(finite, min(config.detector_threshold, 0.999))
            )
        else:
            global_thresholds[metric] = 1.0

    total = len(group_names)
    for g_idx, group_name in enumerate(group_names):
        if progress_cb:
            pct = progress_start + (g_idx / total) * (progress_end - progress_start)
            progress_cb(pct, f"Scoring {group_name}...")

        gdf = aligned[group_name]
        actual_set = actual_timestamps[group_name]
        dim_values = {dim_col: str(group_name)}

        for m_idx, metric in enumerate(metric_cols):
            scores_arr = score_matrix[group_name][:, m_idx]
            threshold = global_thresholds[metric]

            for t_idx, ts_idx in enumerate(common_idx):
                if ts_idx not in actual_set:
                    continue

                ts_str = str(ts_idx)
                score_val = round(float(scores_arr[t_idx]), 6)
                actual_val = float(gdf.iloc[t_idx, m_idx])
                if not math.isfinite(actual_val):
                    actual_val = 0.0

                all_scores.append({
                    "timestamp": ts_str,
                    "metric": metric,
                    "score": score_val,
                    "dimension_values": dim_values,
                })

                if score_val > threshold:
                    anomaly_points.append(DartsAnomalyPoint(
                        timestamp=ts_str,
                        metric=metric,
                        value=round(actual_val, 6),
                        score=score_val,
                        is_anomaly=True,
                        severity=_classify_severity(score_val, threshold),
                        dimension_values=dim_values,
                    ))


# ---------------------------------------------------------------------------
# Peer PCA Reconstruction Error pipeline
# ---------------------------------------------------------------------------

def _run_peer_pca_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """PCA reconstruction error across the peer cohort.

    Stacks all N peer time series as rows of an N x T matrix (per metric).
    PCA captures the shared variation; nodes with high reconstruction error
    are behaving in ways not explained by the group consensus.
    """
    from sklearn.decomposition import PCA as SklearnPCA
    from sklearn.preprocessing import StandardScaler

    n_components = float(config.params.get("n_components", 0.95))

    dim_col, common_idx, aligned, actual_timestamps, _ = _prepare_peer_groups(
        df, ts_col, metric_cols, config, progress_cb,
    )
    group_names = list(aligned.keys())

    if progress_cb:
        progress_cb(20, "Running PCA...")

    # Build score matrix: per-group (T, M) reconstruction error
    score_matrix: dict[str, np.ndarray] = {
        g: np.zeros((len(common_idx), len(metric_cols))) for g in group_names
    }

    for m_idx, metric in enumerate(metric_cols):
        # Build N x T matrix: each row is one node's time series for this metric
        data_matrix = np.array([aligned[g].values[:, m_idx] for g in group_names])  # (N, T)

        # Standardize columns (time steps) so PCA is scale-invariant
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data_matrix)  # (N, T)

        # PCA: retain components explaining n_components% of variance
        n_comp = min(
            max(1, int(n_components * min(data_scaled.shape))),
            min(data_scaled.shape) - 1,
        )
        if n_components < 1.0:
            n_comp = n_components  # let sklearn pick based on variance ratio
        pca = SklearnPCA(n_components=n_comp)
        transformed = pca.fit_transform(data_scaled)     # (N, k)
        reconstructed = pca.inverse_transform(transformed)  # (N, T)

        # Reconstruction error per node per time step
        errors = np.abs(data_scaled - reconstructed)  # (N, T)

        for g_idx, group_name in enumerate(group_names):
            score_matrix[group_name][:, m_idx] = errors[g_idx]

    # Emit consensus as forecast
    if all_forecast_points is not None:
        stacked = np.stack([aligned[g].values for g in group_names], axis=-1)
        consensus = np.nanmedian(stacked, axis=-1)
        for m_idx, metric in enumerate(metric_cols):
            for ts_idx in common_idx:
                t_pos = common_idx.get_loc(ts_idx)
                c_val = float(consensus[t_pos, m_idx])
                if math.isfinite(c_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=str(ts_idx), metric=metric,
                        predicted=round(c_val, 6), actual=round(c_val, 6),
                    ))

    if progress_cb:
        progress_cb(50, "Computing thresholds...")

    _emit_peer_scores_and_anomalies(
        group_names, metric_cols, common_idx, aligned, actual_timestamps,
        score_matrix, dim_col, config, anomaly_points, all_scores,
        progress_cb, 50, 95,
    )

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Peer Functional Depth (Modified Band Depth) pipeline
# ---------------------------------------------------------------------------

def _run_peer_functional_depth_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Functional depth across the peer cohort.

    Combines two measures:
    1. Per-timestamp envelope distance: at each time t, how far outside the
       peer IQR band is this node? (gives per-timestamp variation)
    2. Modified Band Depth (MBD): whole-curve centrality ranking used as a
       multiplier to amplify scores for overall-outlier nodes.

    Final score = envelope_distance * (1 + outlier_weight * (1 - MBD))
    """
    dim_col, common_idx, aligned, actual_timestamps, _ = _prepare_peer_groups(
        df, ts_col, metric_cols, config, progress_cb,
    )
    group_names = list(aligned.keys())
    N = len(group_names)
    T = len(common_idx)

    if progress_cb:
        progress_cb(15, "Computing functional depth...")

    score_matrix: dict[str, np.ndarray] = {
        g: np.zeros((T, len(metric_cols))) for g in group_names
    }

    for m_idx, metric in enumerate(metric_cols):
        # Build N x T matrix
        curves = np.array([aligned[g].values[:, m_idx] for g in group_names])  # (N, T)

        # --- Per-timestamp envelope distance ---
        # At each timestamp, compute median and IQR across peers
        peer_median = np.nanmedian(curves, axis=0)  # (T,)
        q25 = np.nanpercentile(curves, 25, axis=0)  # (T,)
        q75 = np.nanpercentile(curves, 75, axis=0)  # (T,)
        iqr = q75 - q25  # (T,)
        iqr_safe = np.where(iqr > 0, iqr, 1.0)

        # For each node: distance from median, normalized by IQR
        envelope_scores = np.zeros((N, T))
        for i in range(N):
            distance = np.abs(curves[i] - peer_median)
            envelope_scores[i] = distance / iqr_safe

        if progress_cb:
            progress_cb(25 + m_idx * 10, f"MBD for {metric}...")

        # --- Modified Band Depth (whole-curve ranking) ---
        mbd_scores = np.zeros(N)
        for i in range(N):
            depth_sum = 0.0
            pair_count = 0
            for j in range(N):
                if j == i:
                    continue
                for k in range(j + 1, N):
                    if k == i:
                        continue
                    lower = np.minimum(curves[j], curves[k])
                    upper = np.maximum(curves[j], curves[k])
                    inside = (curves[i] >= lower) & (curves[i] <= upper)
                    depth_sum += np.sum(inside) / T
                    pair_count += 1
            if pair_count > 0:
                mbd_scores[i] = depth_sum / pair_count

        # Combine: envelope distance * MBD outlier weight
        # Nodes with low MBD (shallow, overall outlier) get amplified scores
        for g_idx, group_name in enumerate(group_names):
            outlier_weight = 1.0 + (1.0 - mbd_scores[g_idx])  # range [1, 2]
            score_matrix[group_name][:, m_idx] = envelope_scores[g_idx] * outlier_weight

    # Emit consensus (median) as forecast
    if all_forecast_points is not None:
        stacked = np.stack([aligned[g].values for g in group_names], axis=-1)
        consensus = np.nanmedian(stacked, axis=-1)
        for m_idx, metric in enumerate(metric_cols):
            for ts_idx in common_idx:
                t_pos = common_idx.get_loc(ts_idx)
                c_val = float(consensus[t_pos, m_idx])
                if math.isfinite(c_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=str(ts_idx), metric=metric,
                        predicted=round(c_val, 6), actual=round(c_val, 6),
                    ))

    if progress_cb:
        progress_cb(55, "Computing thresholds...")

    _emit_peer_scores_and_anomalies(
        group_names, metric_cols, common_idx, aligned, actual_timestamps,
        score_matrix, dim_col, config, anomaly_points, all_scores,
        progress_cb, 55, 95,
    )

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Peer Feature Isolation Forest pipeline
# ---------------------------------------------------------------------------

def _extract_ts_features(series: np.ndarray) -> np.ndarray:
    """Extract statistical features from a 1-D time series for cohort comparison.

    Returns a feature vector capturing: central tendency, spread, shape,
    autocorrelation, trend, and complexity.
    """
    from scipy import stats as sp_stats

    n = len(series)
    features = []

    # Basic stats
    features.append(np.nanmean(series))
    features.append(np.nanstd(series))
    features.append(float(sp_stats.skew(series, nan_policy='omit')))
    features.append(float(sp_stats.kurtosis(series, nan_policy='omit')))
    features.append(np.nanmedian(series))

    # Range / IQR
    q25, q75 = np.nanpercentile(series, [25, 75])
    features.append(q75 - q25)  # IQR
    features.append(np.nanmax(series) - np.nanmin(series))  # range

    # First-difference stats (captures volatility / smoothness)
    diff = np.diff(series)
    features.append(np.nanstd(diff))
    features.append(np.nanmean(np.abs(diff)))

    # Autocorrelation at lags 1, 5, 10
    centered = series - np.nanmean(series)
    var = np.nanvar(series)
    for lag in [1, 5, 10]:
        if lag < n and var > 0:
            acf = np.nanmean(centered[:-lag] * centered[lag:]) / var
            features.append(acf)
        else:
            features.append(0.0)

    # Trend: slope of linear regression
    x = np.arange(n, dtype=float)
    valid = np.isfinite(series)
    if np.sum(valid) > 2:
        slope, _, _, _, _ = sp_stats.linregress(x[valid], series[valid])
        features.append(slope)
    else:
        features.append(0.0)

    # Zero-crossing rate
    mean_centered = series - np.nanmean(series)
    sign_changes = np.sum(np.diff(np.sign(mean_centered)) != 0)
    features.append(sign_changes / max(n - 1, 1))

    # Spectral entropy (normalized)
    try:
        fft_vals = np.fft.rfft(series - np.nanmean(series))
        power = np.abs(fft_vals) ** 2
        power_norm = power / (np.sum(power) + 1e-12)
        power_norm = power_norm[power_norm > 0]
        spectral_entropy = -np.sum(power_norm * np.log2(power_norm + 1e-12))
        features.append(spectral_entropy)
    except Exception:
        features.append(0.0)

    return np.array(features, dtype=float)


def _run_peer_feature_isolation_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Feature-based Isolation Forest on the peer cohort.

    Extracts statistical features per node (autocorrelation, entropy, trend,
    variance, etc.) and runs Isolation Forest to find nodes whose feature
    fingerprint is unusual within the group.
    """
    from pyod.models.iforest import IForest

    contamination = float(config.params.get("contamination", 0.1))

    dim_col, common_idx, aligned, actual_timestamps, _ = _prepare_peer_groups(
        df, ts_col, metric_cols, config, progress_cb,
    )
    group_names = list(aligned.keys())
    N = len(group_names)
    T = len(common_idx)

    if progress_cb:
        progress_cb(20, "Extracting features...")

    score_matrix: dict[str, np.ndarray] = {
        g: np.zeros((T, len(metric_cols))) for g in group_names
    }

    for m_idx, metric in enumerate(metric_cols):
        # Extract features for each node
        feature_vectors = []
        for g_idx, group_name in enumerate(group_names):
            series = aligned[group_name].values[:, m_idx]
            features = _extract_ts_features(series)
            feature_vectors.append(features)

        feature_matrix = np.array(feature_vectors)  # (N, F)
        # Replace any NaN/Inf in features
        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        if progress_cb:
            progress_cb(30 + m_idx * 10, f"Running Isolation Forest for {metric}...")

        # Isolation Forest
        clf = IForest(
            contamination=min(contamination, (N - 1) / N),
            random_state=42,
        )
        clf.fit(feature_matrix)

        # decision_scores_: higher = more anomalous (pyod convention)
        node_scores = clf.decision_scores_  # (N,)

        # Combine per-node IF score with per-timestamp envelope distance
        # so the chart shows WHEN the divergence happens, not just flat lines
        curves = np.array([aligned[g].values[:, m_idx] for g in group_names])  # (N, T)
        peer_median = np.nanmedian(curves, axis=0)  # (T,)
        iqr = np.nanpercentile(curves, 75, axis=0) - np.nanpercentile(curves, 25, axis=0)
        iqr_safe = np.where(iqr > 0, iqr, 1.0)

        # Normalize IF scores to [0, 1] range for use as weight
        ns_min, ns_max = node_scores.min(), node_scores.max()
        if ns_max > ns_min:
            node_weights = (node_scores - ns_min) / (ns_max - ns_min)
        else:
            node_weights = np.ones(N)

        for g_idx, group_name in enumerate(group_names):
            envelope_dist = np.abs(curves[g_idx] - peer_median) / iqr_safe
            # Weight by IF anomaly score: anomalous nodes get amplified
            score_matrix[group_name][:, m_idx] = envelope_dist * (1.0 + node_weights[g_idx] * 2.0)

    # Emit consensus as forecast
    if all_forecast_points is not None:
        stacked = np.stack([aligned[g].values for g in group_names], axis=-1)
        consensus = np.nanmedian(stacked, axis=-1)
        for m_idx, metric in enumerate(metric_cols):
            for ts_idx in common_idx:
                t_pos = common_idx.get_loc(ts_idx)
                c_val = float(consensus[t_pos, m_idx])
                if math.isfinite(c_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=str(ts_idx), metric=metric,
                        predicted=round(c_val, 6), actual=round(c_val, 6),
                    ))

    if progress_cb:
        progress_cb(55, "Computing thresholds...")

    _emit_peer_scores_and_anomalies(
        group_names, metric_cols, common_idx, aligned, actual_timestamps,
        score_matrix, dim_col, config, anomaly_points, all_scores,
        progress_cb, 55, 95,
    )

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Peer DTW + LOF pipeline
# ---------------------------------------------------------------------------

def _run_peer_dtw_lof_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Dynamic Time Warping + Local Outlier Factor on the peer cohort.

    Computes pairwise DTW distances between all peer time series, then
    applies LOF to find nodes whose shape is most different from neighbours.
    Catches time-shifted patterns that pointwise comparison misses.
    """
    try:
        from dtaidistance import dtw as dtw_lib
    except ImportError:
        raise ImportError(
            "dtaidistance is required for DTW + LOF. "
            "Install with: pip install dtaidistance"
        )
    from sklearn.neighbors import LocalOutlierFactor

    dtw_window = int(config.params.get("dtw_window", 10))
    lof_neighbors = int(config.params.get("lof_neighbors", 3))

    dim_col, common_idx, aligned, actual_timestamps, _ = _prepare_peer_groups(
        df, ts_col, metric_cols, config, progress_cb,
    )
    group_names = list(aligned.keys())
    N = len(group_names)
    T = len(common_idx)

    # Ensure LOF neighbors doesn't exceed available peers
    lof_neighbors = min(lof_neighbors, N - 1)
    if lof_neighbors < 1:
        lof_neighbors = 1

    if progress_cb:
        progress_cb(15, "Computing DTW distances...")

    score_matrix: dict[str, np.ndarray] = {
        g: np.zeros((T, len(metric_cols))) for g in group_names
    }

    for m_idx, metric in enumerate(metric_cols):
        # Extract series for each node
        series_list = []
        for group_name in group_names:
            s = aligned[group_name].values[:, m_idx].astype(np.float64)
            series_list.append(s)

        if progress_cb:
            progress_cb(20 + m_idx * 15, f"DTW distance matrix for {metric}...")

        # Compute pairwise DTW distance matrix
        dist_matrix = np.zeros((N, N))
        for i in range(N):
            for j in range(i + 1, N):
                d = dtw_lib.distance(
                    series_list[i], series_list[j],
                    window=dtw_window,
                    use_pruning=True,
                )
                dist_matrix[i, j] = d
                dist_matrix[j, i] = d

        if progress_cb:
            progress_cb(40 + m_idx * 10, f"LOF for {metric}...")

        # LOF on precomputed distance matrix
        lof = LocalOutlierFactor(
            n_neighbors=lof_neighbors,
            metric="precomputed",
            contamination="auto",
        )
        lof.fit(dist_matrix)

        # negative_outlier_factor_: more negative = more anomalous
        # Convert to positive scores: -LOF (so higher = more anomalous)
        node_scores = -lof.negative_outlier_factor_  # (N,)

        # Combine per-node LOF score with per-timestamp envelope distance
        curves = np.array(series_list)  # (N, T)
        peer_median = np.nanmedian(curves, axis=0)  # (T,)
        iqr = np.nanpercentile(curves, 75, axis=0) - np.nanpercentile(curves, 25, axis=0)
        iqr_safe = np.where(iqr > 0, iqr, 1.0)

        # Normalize LOF scores to [0, 1] for weighting
        ns_min, ns_max = node_scores.min(), node_scores.max()
        if ns_max > ns_min:
            node_weights = (node_scores - ns_min) / (ns_max - ns_min)
        else:
            node_weights = np.ones(N)

        for g_idx, group_name in enumerate(group_names):
            envelope_dist = np.abs(curves[g_idx] - peer_median) / iqr_safe
            score_matrix[group_name][:, m_idx] = envelope_dist * (1.0 + node_weights[g_idx] * 2.0)

    # Emit consensus as forecast
    if all_forecast_points is not None:
        stacked = np.stack([aligned[g].values for g in group_names], axis=-1)
        consensus = np.nanmedian(stacked, axis=-1)
        for m_idx, metric in enumerate(metric_cols):
            for ts_idx in common_idx:
                t_pos = common_idx.get_loc(ts_idx)
                c_val = float(consensus[t_pos, m_idx])
                if math.isfinite(c_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=str(ts_idx), metric=metric,
                        predicted=round(c_val, 6), actual=round(c_val, 6),
                    ))

    if progress_cb:
        progress_cb(55, "Computing thresholds...")

    _emit_peer_scores_and_anomalies(
        group_names, metric_cols, common_idx, aligned, actual_timestamps,
        score_matrix, dim_col, config, anomaly_points, all_scores,
        progress_cb, 55, 95,
    )

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Peer Matrix Profile (MPdist) pipeline
# ---------------------------------------------------------------------------

def _run_peer_matrix_profile_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Matrix Profile distance (MPdist) against peer consensus.

    Uses STUMPY to compute the AB-join matrix profile between each node and
    the consensus time series. The matrix profile captures the distance of
    each subsequence in the node to its nearest match in the consensus.
    High matrix profile values indicate novel shapes not present in the group norm.
    """
    try:
        import stumpy
    except ImportError:
        raise ImportError(
            "stumpy is required for Matrix Profile analysis. "
            "Install with: pip install stumpy"
        )

    subseq_len = int(config.params.get("subsequence_length", 24))

    dim_col, common_idx, aligned, actual_timestamps, _ = _prepare_peer_groups(
        df, ts_col, metric_cols, config, progress_cb,
    )
    group_names = list(aligned.keys())
    N = len(group_names)
    T = len(common_idx)

    # Subsequence length must be < T
    subseq_len = min(subseq_len, T // 2)
    if subseq_len < 4:
        subseq_len = 4

    if progress_cb:
        progress_cb(15, "Computing consensus...")

    # Build consensus (median across peers)
    stacked = np.stack([aligned[g].values for g in group_names], axis=-1)  # (T, M, P)
    consensus = np.nanmedian(stacked, axis=-1)  # (T, M)

    # Emit consensus as forecast
    if all_forecast_points is not None:
        for m_idx, metric in enumerate(metric_cols):
            for ts_idx in common_idx:
                t_pos = common_idx.get_loc(ts_idx)
                c_val = float(consensus[t_pos, m_idx])
                if math.isfinite(c_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=str(ts_idx), metric=metric,
                        predicted=round(c_val, 6), actual=round(c_val, 6),
                    ))

    if progress_cb:
        progress_cb(25, "Computing matrix profiles...")

    score_matrix: dict[str, np.ndarray] = {
        g: np.zeros((T, len(metric_cols))) for g in group_names
    }

    for m_idx, metric in enumerate(metric_cols):
        consensus_series = consensus[:, m_idx].astype(np.float64)

        for g_idx, group_name in enumerate(group_names):
            if progress_cb:
                pct = 25 + ((m_idx * N + g_idx) / (len(metric_cols) * N)) * 35
                progress_cb(pct, f"Matrix profile: {group_name} / {metric}...")

            node_series = aligned[group_name].values[:, m_idx].astype(np.float64)

            # AB-join: matrix profile of node against consensus
            try:
                mp = stumpy.stump(node_series, m=subseq_len, T_B=consensus_series)
                mp_values = mp[:, 0].astype(float)  # nearest-neighbour distances

                # Pad to full length T (MP is shorter by subseq_len-1)
                padded = np.zeros(T)
                # Center the MP values within the time series
                offset = (subseq_len - 1) // 2
                padded[offset:offset + len(mp_values)] = mp_values
                # Fill edges
                if offset > 0:
                    padded[:offset] = mp_values[0]
                remainder = T - offset - len(mp_values)
                if remainder > 0:
                    padded[offset + len(mp_values):] = mp_values[-1]

                score_matrix[group_name][:, m_idx] = padded
            except Exception:
                # Fallback: zero scores if MP computation fails
                score_matrix[group_name][:, m_idx] = 0.0

    if progress_cb:
        progress_cb(60, "Computing thresholds...")

    _emit_peer_scores_and_anomalies(
        group_names, metric_cols, common_idx, aligned, actual_timestamps,
        score_matrix, dim_col, config, anomaly_points, all_scores,
        progress_cb, 60, 95,
    )

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# DAGMM pipeline (Deep Autoencoding Gaussian Mixture Model)
# ---------------------------------------------------------------------------

def _run_dagmm_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """DAGMM: compression autoencoder + GMM estimation network.

    Score = negative log-likelihood under the learned Gaussian mixture.
    """
    import torch
    import torch.nn as nn

    window = max(5, int(config.params.get("window", 20)))
    hidden_dim = int(config.params.get("hidden_dim", 16))
    n_components = int(config.params.get("n_components", 4))
    epochs = int(config.params.get("epochs", 30))
    lr = float(config.params.get("lr", 0.001))
    device = torch.device(_cached_accelerator())

    if progress_cb:
        progress_cb(5, "Preparing data...")

    # --- Data preparation ---
    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    for col in metric_cols:
        if col in work.columns:
            work[col] = work[col].interpolate(method="linear", limit_direction="both")
            work[col] = work[col].ffill().bfill().fillna(0)

    values = work[metric_cols].values.astype(np.float64)
    n_timestamps = len(values)
    n_features = len(metric_cols)

    if n_timestamps < window + 10:
        logger.warning("DAGMM: insufficient data (%d < %d)", n_timestamps, window + 10)
        if progress_cb:
            progress_cb(100, "Insufficient data")
        return

    # Z-score normalize
    mean_val = np.mean(values, axis=0, keepdims=True)
    std_val = np.std(values, axis=0, keepdims=True)
    std_val[std_val < 1e-12] = 1.0
    values_norm = (values - mean_val) / std_val

    # Create sliding windows: (N, window * n_features)
    windows_list = []
    for i in range(n_timestamps - window + 1):
        windows_list.append(values_norm[i:i + window].flatten())
    windows_arr = np.array(windows_list, dtype=np.float32)
    input_dim = window * n_features

    if progress_cb:
        progress_cb(10, "Building DAGMM model...")

    # --- DAGMM model definition ---
    class _CompressionNet(nn.Module):
        def __init__(self, in_dim, latent_dim):
            super().__init__()
            mid = max(in_dim // 4, latent_dim * 2)
            self.encoder = nn.Sequential(
                nn.Linear(in_dim, mid), nn.ReLU(), nn.Dropout(0.1),
                nn.Linear(mid, latent_dim), nn.ReLU(),
            )
            self.decoder = nn.Sequential(
                nn.Linear(latent_dim, mid), nn.ReLU(), nn.Dropout(0.1),
                nn.Linear(mid, in_dim),
            )

        def forward(self, x):
            z = self.encoder(x)
            x_hat = self.decoder(z)
            recon_err = torch.mean((x - x_hat) ** 2, dim=1, keepdim=True)
            cos_sim = nn.functional.cosine_similarity(x, x_hat, dim=1).unsqueeze(1)
            z_combined = torch.cat([z, recon_err, cos_sim], dim=1)
            return z_combined, x_hat

    class _EstimationNet(nn.Module):
        def __init__(self, in_dim, n_comp):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, max(in_dim * 2, 16)), nn.ReLU(), nn.Dropout(0.2),
                nn.Linear(max(in_dim * 2, 16), n_comp), nn.Softmax(dim=1),
            )

        def forward(self, z):
            return self.net(z)

    class _DAGMM(nn.Module):
        def __init__(self, in_dim, latent_dim, n_comp):
            super().__init__()
            z_dim = latent_dim + 2
            self.comp_net = _CompressionNet(in_dim, latent_dim)
            self.est_net = _EstimationNet(z_dim, n_comp)
            self.n_comp = n_comp
            self.z_dim = z_dim

        def forward(self, x):
            z, x_hat = self.comp_net(x)
            gamma = self.est_net(z)
            return z, x_hat, gamma

        def compute_energy(self, z, gamma):
            N = z.size(0)
            gamma_sum = gamma.sum(dim=0)
            phi = gamma_sum / N
            mu = (gamma.unsqueeze(2) * z.unsqueeze(1)).sum(dim=0) / (gamma_sum.unsqueeze(1) + 1e-8)
            z_mu = z.unsqueeze(1) - mu.unsqueeze(0)
            cov_diag = ((gamma.unsqueeze(2) * z_mu ** 2).sum(dim=0)) / (gamma_sum.unsqueeze(1) + 1e-8)
            cov_diag = cov_diag + 1e-6
            log_det = cov_diag.log().sum(dim=1)
            mahal = (z_mu ** 2 / cov_diag.unsqueeze(0)).sum(dim=2)
            log_prob = -0.5 * (self.z_dim * np.log(2 * np.pi) + log_det.unsqueeze(0) + mahal)
            log_prob = log_prob + phi.log().unsqueeze(0)
            energy = -torch.logsumexp(log_prob, dim=1)
            return energy

    model = _DAGMM(input_dim, hidden_dim, n_components).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    X = torch.tensor(windows_arr, dtype=torch.float32).to(device)

    if progress_cb:
        progress_cb(15, "Training DAGMM...")

    # --- Training loop ---
    model.train()
    batch_size = min(256, len(X))
    for epoch in range(epochs):
        perm = torch.randperm(len(X), device=device)
        for start in range(0, len(X), batch_size):
            idx = perm[start:start + batch_size]
            batch = X[idx]
            z, x_hat, gamma = model(batch)
            recon_loss = torch.mean((batch - x_hat) ** 2)
            energy = model.compute_energy(z, gamma)
            energy_loss = torch.mean(energy)
            loss = recon_loss + 0.1 * energy_loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if progress_cb:
            pct = 15 + int(65 * (epoch + 1) / epochs)
            progress_cb(pct, f"Training DAGMM... epoch {epoch + 1}/{epochs}")

    # --- Scoring ---
    if progress_cb:
        progress_cb(85, "Computing anomaly scores...")

    model.eval()
    with torch.no_grad():
        z, x_hat, gamma = model(X)
        energy_scores = model.compute_energy(z, gamma).cpu().numpy()

    # Map window scores back to timestamps (assign to last point of each window)
    timestamp_scores = np.full(n_timestamps, np.nan)
    for i in range(len(energy_scores)):
        t_idx = i + window - 1
        timestamp_scores[t_idx] = energy_scores[i]
    # Fill leading NaN with first valid score
    first_valid = energy_scores[0] if len(energy_scores) > 0 else 0.0
    for i in range(window - 1):
        timestamp_scores[i] = first_valid

    # Normalize scores to [0, 1] range
    s_min, s_max = np.nanmin(timestamp_scores), np.nanmax(timestamp_scores)
    if s_max - s_min > 1e-12:
        timestamp_scores = (timestamp_scores - s_min) / (s_max - s_min)

    # Compute threshold
    valid_scores = timestamp_scores[~np.isnan(timestamp_scores)]
    threshold = float(np.quantile(valid_scores, min(config.detector_threshold, 0.999))) if len(valid_scores) > 0 else 1.0

    # Reconstruct baseline from autoencoder
    recon_all = x_hat.cpu().numpy()
    # Baseline: take the last n_features values from each reconstructed window
    baseline = np.full_like(values, np.nan)
    for i in range(len(recon_all)):
        t_idx = i + window - 1
        recon_window = recon_all[i].reshape(window, n_features)
        baseline[t_idx] = recon_window[-1] * std_val.flatten() + mean_val.flatten()

    # Populate results
    timestamps = work.index
    for m_idx, metric in enumerate(metric_cols):
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(timestamp_scores[j]) if not math.isnan(timestamp_scores[j]) else 0.0
            actual_val = float(values[j, m_idx])

            all_scores.append({
                "timestamp": ts_str,
                "metric": metric,
                "score": round(score_val, 6),
            })

            if score_val > threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str, metric=metric,
                    value=round(actual_val, 6), score=round(score_val, 6),
                    is_anomaly=True, severity=_classify_severity(score_val, threshold),
                ))

            if all_forecast_points is not None and not math.isnan(baseline[j, m_idx]):
                fitted_val = float(baseline[j, m_idx])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str, metric=metric,
                        predicted=round(fitted_val, 6), actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Anomaly Transformer pipeline (Association Discrepancy)
# ---------------------------------------------------------------------------

def _run_anomaly_transformer_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Anomaly Transformer: association discrepancy between learned attention
    and Gaussian prior on temporal distance (Xu et al., ICLR 2022)."""
    import torch
    import torch.nn as nn

    window = max(5, int(config.params.get("window", 20)))
    d_model = int(config.params.get("d_model", 64))
    n_heads = int(config.params.get("n_heads", 4))
    n_layers = int(config.params.get("n_layers", 2))
    epochs = int(config.params.get("epochs", 30))
    lr_val = float(config.params.get("lr", 0.0001))
    device = torch.device(_cached_accelerator())

    if progress_cb:
        progress_cb(5, "Preparing data...")

    # --- Data preparation ---
    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    for col in metric_cols:
        if col in work.columns:
            work[col] = work[col].interpolate(method="linear", limit_direction="both")
            work[col] = work[col].ffill().bfill().fillna(0)

    values = work[metric_cols].values.astype(np.float64)
    n_timestamps = len(values)
    n_features = len(metric_cols)

    if n_timestamps < window + 10:
        logger.warning("Anomaly Transformer: insufficient data")
        if progress_cb:
            progress_cb(100, "Insufficient data")
        return

    mean_val = np.mean(values, axis=0, keepdims=True)
    std_val = np.std(values, axis=0, keepdims=True)
    std_val[std_val < 1e-12] = 1.0
    values_norm = (values - mean_val) / std_val

    # Sliding windows: (N, window, n_features)
    windows_list = []
    for i in range(n_timestamps - window + 1):
        windows_list.append(values_norm[i:i + window])
    windows_arr = np.array(windows_list, dtype=np.float32)

    if progress_cb:
        progress_cb(10, "Building Anomaly Transformer...")

    # --- Model definition ---
    class _AnomalyAttention(nn.Module):
        """Attention layer that computes both series and prior associations."""
        def __init__(self, d_m, n_h):
            super().__init__()
            self.n_h = n_h
            self.d_k = d_m // n_h
            self.W_q = nn.Linear(d_m, d_m)
            self.W_k = nn.Linear(d_m, d_m)
            self.W_v = nn.Linear(d_m, d_m)
            self.out_proj = nn.Linear(d_m, d_m)
            # Learnable prior scale
            self.sigma = nn.Parameter(torch.ones(1))

        def forward(self, x):
            B, L, _ = x.shape
            Q = self.W_q(x).view(B, L, self.n_h, self.d_k).transpose(1, 2)
            K = self.W_k(x).view(B, L, self.n_h, self.d_k).transpose(1, 2)
            V = self.W_v(x).view(B, L, self.n_h, self.d_k).transpose(1, 2)

            # Series association (standard attention)
            scores = torch.matmul(Q, K.transpose(-2, -1)) / (self.d_k ** 0.5)
            series_assoc = torch.softmax(scores, dim=-1)

            # Prior association (Gaussian kernel on temporal distance)
            positions = torch.arange(L, dtype=torch.float32, device=x.device)
            dist = (positions.unsqueeze(0) - positions.unsqueeze(1)) ** 2
            sigma = torch.abs(self.sigma) + 1e-4
            prior_assoc = torch.softmax(-dist / (2 * sigma ** 2), dim=-1)
            prior_assoc = prior_assoc.unsqueeze(0).unsqueeze(0).expand(B, self.n_h, L, L)

            # Output
            out = torch.matmul(series_assoc, V)
            out = out.transpose(1, 2).contiguous().view(B, L, -1)
            out = self.out_proj(out)
            return out, series_assoc, prior_assoc

    class _AnomalyTransformerLayer(nn.Module):
        def __init__(self, d_m, n_h):
            super().__init__()
            self.attn = _AnomalyAttention(d_m, n_h)
            self.norm1 = nn.LayerNorm(d_m)
            self.norm2 = nn.LayerNorm(d_m)
            self.ff = nn.Sequential(nn.Linear(d_m, d_m * 4), nn.GELU(), nn.Linear(d_m * 4, d_m))

        def forward(self, x):
            attn_out, series, prior = self.attn(self.norm1(x))
            x = x + attn_out
            x = x + self.ff(self.norm2(x))
            return x, series, prior

    class _AnomalyTransformer(nn.Module):
        def __init__(self, n_feat, d_m, n_h, n_l, win):
            super().__init__()
            self.input_proj = nn.Linear(n_feat, d_m)
            self.pos_emb = nn.Parameter(torch.randn(1, win, d_m) * 0.02)
            self.layers = nn.ModuleList([_AnomalyTransformerLayer(d_m, n_h) for _ in range(n_l)])
            self.output_proj = nn.Linear(d_m, n_feat)

        def forward(self, x):
            h = self.input_proj(x) + self.pos_emb[:, :x.size(1), :]
            all_series, all_prior = [], []
            for layer in self.layers:
                h, series, prior = layer(h)
                all_series.append(series)
                all_prior.append(prior)
            recon = self.output_proj(h)
            return recon, all_series, all_prior

    at_model = _AnomalyTransformer(n_features, d_model, n_heads, n_layers, window).to(device)
    optimizer = torch.optim.Adam(at_model.parameters(), lr=lr_val)
    X = torch.tensor(windows_arr, dtype=torch.float32).to(device)

    if progress_cb:
        progress_cb(15, "Training Anomaly Transformer...")

    # --- Training (minimax on association discrepancy) ---
    batch_size = min(256, len(X))
    at_model.train()
    for epoch in range(epochs):
        perm = torch.randperm(len(X), device=device)
        for start in range(0, len(X), batch_size):
            idx = perm[start:start + batch_size]
            batch = X[idx]
            recon, all_series, all_prior = at_model(batch)

            # Reconstruction loss
            recon_loss = torch.mean((batch - recon) ** 2)

            # Association discrepancy: KL(series || prior) across layers
            kl_total = torch.tensor(0.0, device=device)
            for s_assoc, p_assoc in zip(all_series, all_prior):
                s_clamped = s_assoc.clamp(min=1e-8)
                p_clamped = p_assoc.clamp(min=1e-8)
                kl_total = kl_total + torch.mean(s_clamped * (s_clamped.log() - p_clamped.log()))

            # Phase 1: minimize recon + maximize KL (push series away from prior)
            # Phase 2: minimize KL (bring series toward prior)
            # Simplified: alternate sign of KL term
            if epoch % 2 == 0:
                loss = recon_loss - 0.01 * kl_total
            else:
                loss = recon_loss + 0.01 * kl_total

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if progress_cb:
            pct = 15 + int(65 * (epoch + 1) / epochs)
            progress_cb(pct, f"Training Anomaly Transformer... epoch {epoch + 1}/{epochs}")

    # --- Scoring ---
    if progress_cb:
        progress_cb(85, "Computing association discrepancy scores...")

    at_model.eval()
    with torch.no_grad():
        recon, all_series, all_prior = at_model(X)
        # Score = reconstruction error + association discrepancy per window
        recon_err = torch.mean((X - recon) ** 2, dim=(1, 2)).cpu().numpy()
        kl_scores = torch.zeros(len(X), device=device)
        for s_assoc, p_assoc in zip(all_series, all_prior):
            s_clamped = s_assoc.clamp(min=1e-8)
            p_clamped = p_assoc.clamp(min=1e-8)
            kl_per_sample = torch.mean(s_clamped * (s_clamped.log() - p_clamped.log()), dim=(1, 2, 3))
            kl_scores += kl_per_sample
        kl_np = kl_scores.cpu().numpy()

    # Combined score: reconstruction error + association discrepancy
    combined = recon_err + kl_np

    # Map to timestamps (last point of each window)
    timestamp_scores = np.full(n_timestamps, np.nan)
    for i in range(len(combined)):
        timestamp_scores[i + window - 1] = combined[i]
    first_valid = combined[0] if len(combined) > 0 else 0.0
    for i in range(window - 1):
        timestamp_scores[i] = first_valid

    # Normalize to [0, 1]
    s_min, s_max = np.nanmin(timestamp_scores), np.nanmax(timestamp_scores)
    if s_max - s_min > 1e-12:
        timestamp_scores = (timestamp_scores - s_min) / (s_max - s_min)

    threshold = float(np.quantile(timestamp_scores[~np.isnan(timestamp_scores)],
                                  min(config.detector_threshold, 0.999)))

    # Reconstruction baseline
    recon_np = recon.cpu().numpy()
    baseline = np.full_like(values, np.nan)
    for i in range(len(recon_np)):
        t_idx = i + window - 1
        baseline[t_idx] = recon_np[i, -1, :] * std_val.flatten() + mean_val.flatten()

    # Populate results
    timestamps = work.index
    for m_idx, metric in enumerate(metric_cols):
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(timestamp_scores[j]) if not math.isnan(timestamp_scores[j]) else 0.0
            actual_val = float(values[j, m_idx])

            all_scores.append({
                "timestamp": ts_str, "metric": metric, "score": round(score_val, 6),
            })

            if score_val > threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str, metric=metric,
                    value=round(actual_val, 6), score=round(score_val, 6),
                    is_anomaly=True, severity=_classify_severity(score_val, threshold),
                ))

            if all_forecast_points is not None and not math.isnan(baseline[j, m_idx]):
                fitted_val = float(baseline[j, m_idx])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str, metric=metric,
                        predicted=round(fitted_val, 6), actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# TranAD pipeline (Transformer-based Adversarial Anomaly Detection)
# ---------------------------------------------------------------------------

def _run_tranad_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """TranAD: two-phase adversarial transformer for anomaly detection."""
    import torch
    import torch.nn as nn

    window = max(5, int(config.params.get("window", 20)))
    d_model = int(config.params.get("d_model", 64))
    n_heads = int(config.params.get("n_heads", 4))
    n_layers_param = int(config.params.get("n_layers", 2))
    epochs = int(config.params.get("epochs", 30))
    lr_val = float(config.params.get("lr", 0.0001))
    device = torch.device(_cached_accelerator())

    if progress_cb:
        progress_cb(5, "Preparing data...")

    # --- Data preparation ---
    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    for col in metric_cols:
        if col in work.columns:
            work[col] = work[col].interpolate(method="linear", limit_direction="both")
            work[col] = work[col].ffill().bfill().fillna(0)

    values = work[metric_cols].values.astype(np.float64)
    n_timestamps = len(values)
    n_features = len(metric_cols)

    if n_timestamps < window + 10:
        logger.warning("TranAD: insufficient data")
        if progress_cb:
            progress_cb(100, "Insufficient data")
        return

    mean_val = np.mean(values, axis=0, keepdims=True)
    std_val = np.std(values, axis=0, keepdims=True)
    std_val[std_val < 1e-12] = 1.0
    values_norm = (values - mean_val) / std_val

    windows_list = []
    for i in range(n_timestamps - window + 1):
        windows_list.append(values_norm[i:i + window])
    windows_arr = np.array(windows_list, dtype=np.float32)

    if progress_cb:
        progress_cb(10, "Building TranAD model...")

    # --- TranAD model ---
    class _TranAD(nn.Module):
        def __init__(self, n_feat, d_m, n_h, n_l, win):
            super().__init__()
            self.input_proj = nn.Linear(n_feat, d_m)
            self.pos_emb = nn.Parameter(torch.randn(1, win, d_m) * 0.02)

            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_m, nhead=n_h, dim_feedforward=d_m * 4,
                dropout=0.1, batch_first=True,
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_l)

            decoder_layer1 = nn.TransformerDecoderLayer(
                d_model=d_m, nhead=n_h, dim_feedforward=d_m * 4,
                dropout=0.1, batch_first=True,
            )
            self.decoder1 = nn.TransformerDecoder(decoder_layer1, num_layers=n_l)

            decoder_layer2 = nn.TransformerDecoderLayer(
                d_model=d_m, nhead=n_h, dim_feedforward=d_m * 4,
                dropout=0.1, batch_first=True,
            )
            self.decoder2 = nn.TransformerDecoder(decoder_layer2, num_layers=n_l)

            self.output1 = nn.Linear(d_m, n_feat)
            self.output2 = nn.Linear(d_m, n_feat)

        def forward(self, x):
            h = self.input_proj(x) + self.pos_emb[:, :x.size(1), :]
            memory = self.encoder(h)
            dec1 = self.decoder1(h, memory)
            recon1 = self.output1(dec1)
            # Decoder 2 uses residual from decoder 1 as query
            residual = x - recon1
            h_res = self.input_proj(residual) + self.pos_emb[:, :x.size(1), :]
            dec2 = self.decoder2(h_res, memory)
            recon2 = self.output2(dec2)
            return recon1, recon2

    tranad_model = _TranAD(n_features, d_model, n_heads, n_layers_param, window).to(device)
    optimizer = torch.optim.Adam(tranad_model.parameters(), lr=lr_val)
    X = torch.tensor(windows_arr, dtype=torch.float32).to(device)

    if progress_cb:
        progress_cb(15, "Training TranAD...")

    # --- Two-phase training ---
    batch_size = min(256, len(X))
    tranad_model.train()
    for epoch in range(epochs):
        perm = torch.randperm(len(X), device=device)
        for start in range(0, len(X), batch_size):
            idx = perm[start:start + batch_size]
            batch = X[idx]
            recon1, recon2 = tranad_model(batch)

            loss1 = torch.mean((batch - recon1) ** 2)
            loss2 = torch.mean((batch - recon2) ** 2)

            # Phase weighting: gradually increase adversarial component
            alpha = min(1.0, (epoch + 1) / max(epochs * 0.5, 1))
            loss = (1 - alpha) * loss1 + alpha * loss2

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if progress_cb:
            pct = 15 + int(65 * (epoch + 1) / epochs)
            progress_cb(pct, f"Training TranAD... epoch {epoch + 1}/{epochs}")

    # --- Scoring ---
    if progress_cb:
        progress_cb(85, "Computing anomaly scores...")

    tranad_model.eval()
    with torch.no_grad():
        recon1, recon2 = tranad_model(X)
        err1 = torch.mean((X - recon1) ** 2, dim=(1, 2)).cpu().numpy()
        err2 = torch.mean((X - recon2) ** 2, dim=(1, 2)).cpu().numpy()

    # Combined score: average of both decoders
    combined = 0.5 * err1 + 0.5 * err2

    # Map to timestamps
    timestamp_scores = np.full(n_timestamps, np.nan)
    for i in range(len(combined)):
        timestamp_scores[i + window - 1] = combined[i]
    first_valid = combined[0] if len(combined) > 0 else 0.0
    for i in range(window - 1):
        timestamp_scores[i] = first_valid

    s_min, s_max = np.nanmin(timestamp_scores), np.nanmax(timestamp_scores)
    if s_max - s_min > 1e-12:
        timestamp_scores = (timestamp_scores - s_min) / (s_max - s_min)

    threshold = float(np.quantile(timestamp_scores[~np.isnan(timestamp_scores)],
                                  min(config.detector_threshold, 0.999)))

    # Baseline from decoder 1 (standard reconstruction)
    recon1_np = recon1.cpu().numpy()
    baseline = np.full_like(values, np.nan)
    for i in range(len(recon1_np)):
        t_idx = i + window - 1
        baseline[t_idx] = recon1_np[i, -1, :] * std_val.flatten() + mean_val.flatten()

    # Populate results
    timestamps = work.index
    for m_idx, metric in enumerate(metric_cols):
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(timestamp_scores[j]) if not math.isnan(timestamp_scores[j]) else 0.0
            actual_val = float(values[j, m_idx])

            all_scores.append({
                "timestamp": ts_str, "metric": metric, "score": round(score_val, 6),
            })

            if score_val > threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str, metric=metric,
                    value=round(actual_val, 6), score=round(score_val, 6),
                    is_anomaly=True, severity=_classify_severity(score_val, threshold),
                ))

            if all_forecast_points is not None and not math.isnan(baseline[j, m_idx]):
                fitted_val = float(baseline[j, m_idx])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str, metric=metric,
                        predicted=round(fitted_val, 6), actual=round(actual_val, 6),
                    ))

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# MOMENT pipeline (CMU foundation model for anomaly detection)
# ---------------------------------------------------------------------------

_moment_model_cache: dict[str, object] = {}


def _run_moment_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """MOMENT: pre-trained foundation model using reconstruction-based scoring."""
    import torch

    context_length = int(config.params.get("context_length", 512))
    model_variant = str(config.params.get("model_variant", "AutonLab/MOMENT-1-large"))
    device_str = _cached_accelerator()

    if progress_cb:
        progress_cb(5, "Loading MOMENT model...")

    # Lazy-load model
    cache_key = f"{model_variant}|{device_str}"
    if cache_key not in _moment_model_cache:
        try:
            from momentfm import MOMENTPipeline
            pipe = MOMENTPipeline.from_pretrained(
                model_variant,
                model_kwargs={"task_name": "reconstruction"},
            )
            pipe.init()
            device = torch.device(device_str)
            pipe = pipe.to(device)
            _moment_model_cache[cache_key] = pipe
            logger.info("MOMENT model loaded: %s on %s", model_variant, device_str)
        except ImportError:
            raise RuntimeError(
                "MOMENT requires the 'momentfm' package which is not installed. "
                "Run natively with: pip install momentfm"
            )
    pipe = _moment_model_cache[cache_key]
    device = next(pipe.parameters()).device

    if progress_cb:
        progress_cb(15, "Preparing data...")

    # --- Data preparation ---
    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    for col in metric_cols:
        if col in work.columns:
            work[col] = work[col].interpolate(method="linear", limit_direction="both")
            work[col] = work[col].ffill().bfill().fillna(0)

    values = work[metric_cols].values.astype(np.float64)
    n_timestamps = len(values)
    timestamps = work.index
    total_metrics = len(metric_cols)

    if progress_cb:
        progress_cb(20, "Running MOMENT reconstruction...")

    # Process each metric independently (MOMENT expects univariate input)
    for m_idx, metric in enumerate(metric_cols):
        series = values[:, m_idx].copy()

        # Create non-overlapping windows of context_length
        # Pad if necessary
        n_windows = max(1, -(-n_timestamps // context_length))
        padded_len = n_windows * context_length
        padded = np.zeros(padded_len, dtype=np.float32)
        padded[:n_timestamps] = series.astype(np.float32)

        # Normalize
        s_mean = np.mean(series)
        s_std = np.std(series)
        if s_std < 1e-12:
            s_std = 1.0
        padded = (padded - s_mean) / s_std

        # Reshape to (n_windows, 1, context_length) for MOMENT
        windows_tensor = torch.tensor(
            padded.reshape(n_windows, 1, context_length),
            dtype=torch.float32,
        ).to(device)

        # Create input mask (1 = valid, 0 = padding)
        input_mask = torch.ones(n_windows, context_length, dtype=torch.long, device=device)
        if padded_len > n_timestamps:
            last_window_valid = n_timestamps - (n_windows - 1) * context_length
            input_mask[-1, last_window_valid:] = 0

        # Run reconstruction (keyword-only args)
        with torch.no_grad():
            output = pipe.reconstruct(x_enc=windows_tensor, input_mask=input_mask)
            recon = output.reconstruction  # (n_windows, 1, context_length)

        recon_np = recon.cpu().numpy().reshape(-1)[:n_timestamps]
        # Denormalize reconstruction
        recon_denorm = recon_np * s_std + s_mean

        # Score = squared reconstruction error
        padded_input = padded[:n_timestamps]
        recon_scores = (padded_input - recon_np[:n_timestamps]) ** 2

        # Normalize scores
        sc_min, sc_max = np.min(recon_scores), np.max(recon_scores)
        if sc_max - sc_min > 1e-12:
            recon_scores = (recon_scores - sc_min) / (sc_max - sc_min)

        threshold = float(np.quantile(recon_scores, min(config.detector_threshold, 0.999)))

        # Populate results
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(recon_scores[j])
            actual_val = float(series[j])

            all_scores.append({
                "timestamp": ts_str, "metric": metric, "score": round(score_val, 6),
            })

            if score_val > threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str, metric=metric,
                    value=round(actual_val, 6), score=round(score_val, 6),
                    is_anomaly=True, severity=_classify_severity(score_val, threshold),
                ))

            if all_forecast_points is not None:
                fitted_val = float(recon_denorm[j])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str, metric=metric,
                        predicted=round(fitted_val, 6), actual=round(actual_val, 6),
                    ))

        if progress_cb:
            pct = 20 + int(75 * (m_idx + 1) / total_metrics)
            progress_cb(pct, f"MOMENT: {metric}...")

    if progress_cb:
        progress_cb(100, "Done")


# ---------------------------------------------------------------------------
# Lag-Llama pipeline (probabilistic forecasting for anomaly detection)
# ---------------------------------------------------------------------------

_lag_llama_model_cache: dict[str, object] = {}


def _run_lag_llama_pipeline(
    df: pd.DataFrame,
    ts_col: str,
    metric_cols: list[str],
    config: DartsDetectionConfig,
    anomaly_points: list[DartsAnomalyPoint],
    all_scores: list[dict],
    all_forecast_points: list[ForecastPoint] | None = None,
    progress_cb: Callable | None = None,
):
    """Lag-Llama: pre-trained probabilistic forecaster for anomaly detection.

    Score = |actual - median_prediction| / prediction_std.
    """
    import torch

    context_length = int(config.params.get("context_length", 32))
    prediction_length = int(config.params.get("prediction_length", 1))
    num_samples = int(config.params.get("num_samples", 100))
    device_str = _cached_accelerator()

    if progress_cb:
        progress_cb(5, "Loading Lag-Llama model...")

    # Lazy-load model
    if device_str not in _lag_llama_model_cache:
        try:
            from huggingface_hub import hf_hub_download
            ckpt_path = hf_hub_download(
                repo_id="time-series-foundation-models/Lag-Llama",
                filename="lag-llama.ckpt",
            )
            from lag_llama.gluon.estimator import LagLlamaEstimator
            estimator = LagLlamaEstimator(
                ckpt_path=ckpt_path,
                prediction_length=prediction_length,
                context_length=context_length,
                input_size=1,
                n_layer=8,
                n_embd_per_head=32,
                n_head=4,
                num_samples=num_samples,
                device=torch.device(device_str),
            )
            predictor = estimator.create_lightning_module().to(torch.device(device_str))
            _lag_llama_model_cache[device_str] = {
                "ckpt_path": ckpt_path,
                "device": device_str,
            }
            logger.info("Lag-Llama model loaded on %s", device_str)
        except ImportError:
            raise RuntimeError(
                "Lag-Llama requires the 'lag-llama' package which is not installed. "
                "Run natively with: pip install git+https://github.com/time-series-foundation-models/lag-llama.git"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load Lag-Llama: {e}")

    if progress_cb:
        progress_cb(15, "Preparing data...")

    # --- Data preparation ---
    work = df[[ts_col] + [c for c in metric_cols if c in df.columns]].copy()
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    if work[ts_col].duplicated().any():
        work = work.groupby(ts_col, as_index=False)[metric_cols].mean()
        work = work.sort_values(ts_col)
    work = work.set_index(ts_col)

    for col in metric_cols:
        if col in work.columns:
            work[col] = work[col].interpolate(method="linear", limit_direction="both")
            work[col] = work[col].ffill().bfill().fillna(0)

    values = work[metric_cols].values.astype(np.float64)
    n_timestamps = len(values)
    timestamps = work.index
    total_metrics = len(metric_cols)

    if progress_cb:
        progress_cb(20, "Running Lag-Llama forecasting...")

    # Use simpler rolling-window approach with Lag-Llama via GluonTS
    try:
        from huggingface_hub import hf_hub_download
        from lag_llama.gluon.estimator import LagLlamaEstimator
        import torch

        ckpt_info = _lag_llama_model_cache[device_str]
        ckpt_path = ckpt_info["ckpt_path"]
        device = torch.device(device_str)

        estimator = LagLlamaEstimator(
            ckpt_path=ckpt_path,
            prediction_length=prediction_length,
            context_length=context_length,
            input_size=1,
            n_layer=8,
            n_embd_per_head=32,
            n_head=4,
            num_samples=num_samples,
            device=device,
        )
        predictor = estimator.create_predictor(batch_size=64)

    except Exception as e:
        logger.error("Lag-Llama predictor creation failed: %s", e)
        if progress_cb:
            progress_cb(100, f"Error: {e}")
        return

    # Process each metric
    for m_idx, metric in enumerate(metric_cols):
        series = values[:, m_idx].copy()

        # Rolling forecast: for each position i >= context_length, predict and score
        all_preds_median = np.full(n_timestamps, np.nan)
        all_preds_std = np.full(n_timestamps, np.nan)
        metric_scores = np.zeros(n_timestamps)

        # Use GluonTS-style dataset for batch prediction
        from gluonts.dataset.pandas import PandasDataset
        freq = pd.infer_freq(timestamps)
        if freq is None:
            diffs = pd.Series(timestamps).diff().dropna()
            freq = diffs.mode().iloc[0] if len(diffs) > 0 else "h"

        # Create rolling windows as separate GluonTS entries
        entries = []
        valid_indices = []
        stride = max(1, prediction_length)
        for i in range(context_length, n_timestamps, stride):
            ctx_start = max(0, i - context_length)
            entry_series = pd.Series(
                series[ctx_start:i],
                index=timestamps[ctx_start:i],
            )
            entries.append(entry_series)
            valid_indices.append(i)

        if not entries:
            continue

        # Batch predict
        try:
            dataset = PandasDataset(dict(enumerate(entries)), freq=freq)
            forecasts = list(predictor.predict(dataset))

            for fc_idx, forecast in enumerate(forecasts):
                t_idx = valid_indices[fc_idx]
                if t_idx < n_timestamps:
                    samples = forecast.samples[:, 0]  # (num_samples,)
                    median_pred = float(np.median(samples))
                    std_pred = float(np.std(samples))
                    all_preds_median[t_idx] = median_pred
                    all_preds_std[t_idx] = std_pred

                    if std_pred > 1e-12:
                        metric_scores[t_idx] = abs(series[t_idx] - median_pred) / std_pred
                    else:
                        metric_scores[t_idx] = abs(series[t_idx] - median_pred)
        except Exception as e:
            logger.warning("Lag-Llama prediction failed for %s: %s", metric, e)
            # Fallback: simple z-score
            s_mean = np.mean(series)
            s_std = np.std(series)
            if s_std < 1e-12:
                s_std = 1.0
            metric_scores = np.abs(series - s_mean) / s_std

        # Normalize scores
        valid_scores = metric_scores[metric_scores > 0]
        if len(valid_scores) > 0:
            sc_max = np.max(valid_scores)
            if sc_max > 1e-12:
                metric_scores = metric_scores / sc_max

        threshold = float(np.quantile(metric_scores[metric_scores > 0],
                                      min(config.detector_threshold, 0.999))) if len(valid_scores) > 0 else 1.0

        # Populate results
        for j, ts_idx in enumerate(timestamps):
            ts_str = str(ts_idx)
            score_val = float(metric_scores[j])
            actual_val = float(series[j])

            all_scores.append({
                "timestamp": ts_str, "metric": metric, "score": round(score_val, 6),
            })

            if score_val > threshold:
                anomaly_points.append(DartsAnomalyPoint(
                    timestamp=ts_str, metric=metric,
                    value=round(actual_val, 6), score=round(score_val, 6),
                    is_anomaly=True, severity=_classify_severity(score_val, threshold),
                ))

            if all_forecast_points is not None and not math.isnan(all_preds_median[j]):
                fitted_val = float(all_preds_median[j])
                if math.isfinite(fitted_val) and math.isfinite(actual_val):
                    all_forecast_points.append(ForecastPoint(
                        timestamp=ts_str, metric=metric,
                        predicted=round(fitted_val, 6), actual=round(actual_val, 6),
                    ))

        if progress_cb:
            pct = 20 + int(75 * (m_idx + 1) / total_metrics)
            progress_cb(pct, f"Lag-Llama: {metric}...")

    if progress_cb:
        progress_cb(100, "Done")


def run_darts_detection(
    df: pd.DataFrame,
    ts_col: str,
    config: DartsDetectionConfig,
    progress_callback: Callable | None = None,
) -> DartsAnomalyResult:
    """Main entry point. Runs Darts anomaly detection on the given DataFrame."""
    import random
    import numpy as np
    from .registry import get_model

    # Set random seed for reproducibility if provided
    seed = getattr(config, "random_seed", None)
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        try:
            import torch
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except ImportError:
            pass

    model_info = get_model(config.model_id)
    if model_info is None:
        raise ValueError(f"Unknown model: {config.model_id}")

    # Prepare data
    df = df.copy()
    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.dropna(subset=[ts_col]).sort_values(ts_col)

    metric_cols = [m for m in config.metrics if m in df.columns]
    if not metric_cols:
        raise ValueError("No valid metric columns found in data")

    # Save original data before transforms (volume gate needs untransformed values)
    df_original = df.copy() if config.volume_gate_metric else None

    # Apply data infill if requested (before smoothing/transforms)
    infill = getattr(config, "infill", "none")
    if infill and infill != "none":
        df = apply_infill(df, metric_cols, infill, ts_col=ts_col)

    # Apply rolling mean smoothing if requested
    sw = getattr(config, "smoothing_window", 1)
    if sw and sw > 1:
        for col in metric_cols:
            df[col] = df[col].rolling(window=sw, min_periods=1, center=True).mean()

    # Apply data transforms if requested
    transforms = getattr(config, "transforms", [])
    if transforms:
        df = apply_transforms(df, metric_cols, transforms)

    anomaly_points: list[DartsAnomalyPoint] = []
    all_scores: list[dict] = []
    all_forecast_points: list[ForecastPoint] = []

    if config.model_id == DartsModelId.PEER_DIVERGENCE:
        _run_peer_divergence_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.PEER_PCA:
        _run_peer_pca_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.PEER_FUNCTIONAL_DEPTH:
        _run_peer_functional_depth_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.PEER_FEATURE_ISOLATION:
        _run_peer_feature_isolation_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.PEER_DTW_LOF:
        _run_peer_dtw_lof_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.PEER_MATRIX_PROFILE:
        _run_peer_matrix_profile_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.TSPULSE:
        _run_tspulse_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.STL_GESD:
        _run_stl_gesd_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.SPECTRAL_RESIDUAL:
        _run_spectral_residual_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.CUSUM:
        _run_cusum_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.HAMPEL:
        _run_hampel_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.CHANGEPOINT:
        _run_changepoint_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.MODIFIED_ZSCORE:
        _run_modified_zscore_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.DAGMM:
        _run_dagmm_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.ANOMALY_TRANSFORMER:
        _run_anomaly_transformer_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.TRANAD:
        _run_tranad_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.MOMENT:
        _run_moment_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id == DartsModelId.LAG_LLAMA:
        _run_lag_llama_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif model_info.category == "scorer":
        _run_scorer_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    elif config.model_id in GLOBAL_FORECAST_MODELS:
        _run_global_forecast_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )
    else:
        _run_forecast_pipeline(
            df, ts_col, metric_cols, config,
            anomaly_points, all_scores, all_forecast_points, progress_callback,
        )

    # --- Post-processing: volume gate ---
    if config.volume_gate_metric and config.volume_gate_threshold > 0 and df_original is not None:
        anomaly_points = _apply_volume_gate(
            anomaly_points, df_original, ts_col,
            config.volume_gate_metric, config.volume_gate_threshold,
        )

    regions = _merge_into_regions(anomaly_points)

    # --- Post-processing: persistence damping ---
    damping = config.persistence_damping
    min_pts = config.min_anomaly_points
    if damping > 0 or min_pts > 1:
        # Compute global threshold from all scores for severity re-classification
        score_vals = [s["score"] for s in all_scores if isinstance(s.get("score"), (int, float))]
        score_arr = np.array(score_vals) if score_vals else np.array([1.0])
        score_arr = score_arr[~np.isnan(score_arr)]
        global_threshold = float(
            np.quantile(score_arr, min(config.detector_threshold, 0.999))
        ) if len(score_arr) > 0 else 1.0

        regions, anomaly_points = _apply_persistence_damping(
            regions, anomaly_points, damping, min_pts, global_threshold,
        )

    summary = AnomalySummary(
        total_points_analyzed=len(df),
        total_anomalies=len(anomaly_points),
        total_regions=len(regions),
        by_severity={
            "low": sum(1 for p in anomaly_points if p.severity == "low"),
            "medium": sum(1 for p in anomaly_points if p.severity == "medium"),
            "high": sum(1 for p in anomaly_points if p.severity == "high"),
        },
        by_metric={
            metric: sum(1 for p in anomaly_points if p.metric == metric)
            for metric in metric_cols
        },
    )

    return DartsAnomalyResult(
        run_id="",
        config=config,
        anomalies=anomaly_points,
        scores=all_scores,
        forecast=all_forecast_points if all_forecast_points else None,
        summary=summary,
        regions=regions,
    )
