# Anomaly Detection Playground — Model Catalog

**63 models** across anomaly scoring and time series forecasting, with **21 GPU-accelerated** models leveraging Apple Silicon (MPS) or NVIDIA CUDA.

---

## Anomaly Scorers (35 models)

Scorers compute anomaly scores directly, without forecasting. Higher scores indicate more anomalous behavior.

### Statistical / Signal Processing

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| Modified Z-Score | `modified_zscore` | Robust z-score using median and MAD — resilient to existing outliers | |
| STL + GESD | `stl_gesd` | STL seasonal decomposition followed by Generalized ESD test on residuals | |
| Spectral Residual | `spectral_residual` | Microsoft's FFT-based saliency map detects spectral anomalies | |
| CUSUM | `cusum` | Cumulative sum control chart — detects level shifts (two-sided) | |
| Hampel Filter | `hampel` | Sliding-window median + MAD-based outlier detection | |
| Change Point Detection | `changepoint` | PELT algorithm (ruptures) finds structural breaks in the series | |

### Density / Distance-Based (PyOD)

These use the [PyOD](https://github.com/yzhao062/pyod) library, wrapped via Darts `PyODScorer` for sliding-window anomaly scoring.

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| K-Means | `kmeans` | Darts native k-means scorer on sliding windows | |
| Isolation Forest | `isolation_forest` | Ensemble of random trees isolating anomalies quickly | |
| Local Outlier Factor | `lof` | Density-based: compares each point's local density to its neighbors | |
| ECOD | `ecod` | Empirical Cumulative Distribution — unsupervised, parameter-free | |
| Wasserstein | `wasserstein` | Darts native scorer using Wasserstein distance between windows | |
| COPOD | `copod` | Copula-based Outlier Detection — fast, parameter-free | |
| HBOS | `hbos` | Histogram-Based Outlier Score — extremely fast, assumption-free | |
| KNN | `knn` | K-Nearest Neighbors distance-based outlier detection | |
| OC-SVM | `ocsvm` | One-Class SVM — kernel-based boundary for normal data | |
| INNE | `inne` | Isolation-based Nearest Neighbor Ensemble | |
| LODA | `loda` | Lightweight Online Detector of Anomalies — random projection histograms | |
| CBLOF | `cblof` | Cluster-Based Local Outlier Factor | |
| ROD | `rod` | Rotation-based Outlier Detection | |
| ABOD | `abod` | Angle-Based Outlier Detection — uses variance of angles between points | |
| SOS | `sos` | Stochastic Outlier Selection — affinity-based probabilistic scoring | |
| LSCP | `lscp` | Locally Selective Combination of Parallel detectors (meta-ensemble) | |
| SOD | `sod` | Subspace Outlier Detection — finds anomalies in axis-aligned subspaces | |
| VAE | `vae` | Variational Autoencoder — probabilistic latent space, reconstruction probability scoring | Yes |
| PCA | `pca` | Principal Component Analysis — reconstruction error from retained components | |
| MCD | `mcd` | Minimum Covariance Determinant — robust Mahalanobis distance from data center | |

### Deep Learning Scorers

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| Deep SVDD | `deep_svdd` | Neural network mapping to compact hypersphere; distance from center = score | Yes |
| AutoEncoder (PyTorch) | `autoencoder` | Deep autoencoder reconstruction error as anomaly score | Yes |
| DAGMM | `dagmm` | Deep Autoencoding Gaussian Mixture Model — autoencoder + GMM energy scoring | Yes |
| Anomaly Transformer | `anomaly_transformer` | Association discrepancy between learned attention and Gaussian prior (ICLR 2022) | Yes |
| TranAD | `tranad` | Transformer-based adversarial two-phase training for anomaly detection | Yes |

### Foundation Model Scorers

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| TSPulse (IBM Granite) | `tspulse` | IBM's foundation model — time + frequency reconstruction scoring. Zero-shot. | Yes |
| MOMENT (CMU) | `moment` | CMU's pre-trained foundation model for reconstruction-based anomaly detection. Zero-shot. | Yes |
| Lag-Llama | `lag_llama` | LLaMA-based probabilistic forecaster — anomalies fall outside prediction intervals. Zero-shot. | Yes |

### Peer / Comparative

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| Peer Divergence | `peer_divergence` | Detects when a dimension diverges from its peers (group consensus) | |

---

## Forecast Models (28 models)

Forecast models predict expected values; anomalies are detected when actual values deviate significantly from predictions. A separate detector (quantile, threshold, or IQR) converts the residuals into binary anomaly decisions.

### Classical / Statistical

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| Naive Mean | `naive_mean` | Predicts the historical mean | |
| Naive Seasonal | `naive_seasonal` | Repeats the last observed seasonal cycle | |
| Naive Drift | `naive_drift` | Linear extrapolation from first to last observation | |
| Naive Moving Average | `naive_moving_avg` | Rolling average as prediction | |
| Exponential Smoothing | `exponential_smoothing` | Holt-Winters with automatic trend and seasonality | |
| Theta | `theta` | Assimakopoulos & Nikolopoulos Theta method | |
| Four Theta | `four_theta` | Optimized four-parameter Theta method | |
| FFT | `fft` | Fast Fourier Transform extrapolation for periodic data | |
| ARIMA | `arima` | Classic autoregressive integrated moving average | |
| Auto ARIMA | `auto_arima` | Automatic ARIMA order selection (via statsforecast) | |
| Croston | `croston` | Designed for intermittent/sparse demand time series | |
| Prophet | `prophet` | Meta's decomposable forecaster with trend, seasonality, and holidays | |

### Machine Learning (sklearn-style)

Global models trained once on all data, then predict without retraining per window.

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| Linear Regression | `linear_regression` | Lags-based linear model | |
| Random Forest | `random_forest` | Ensemble of decision trees on lagged features | |
| LightGBM | `lightgbm` | Gradient boosting on lagged features (fast) | |
| XGBoost | `xgboost` | Extreme gradient boosting on lagged features | |

### Deep Learning

All deep learning forecasters support GPU acceleration via MPS (Apple Silicon) or CUDA.

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| DLinear | `dlinear` | Simple linear decomposition — competitive baseline | Yes |
| NLinear | `nlinear` | Normalized linear model for non-stationary series | Yes |
| N-BEATS | `nbeats` | Neural Basis Expansion — stacks of fully connected networks | Yes |
| N-HiTS | `nhits` | Neural Hierarchical Interpolation — multi-resolution N-BEATS | Yes |
| TCN | `tcn` | Temporal Convolutional Network with dilated causal convolutions | Yes |
| Block RNN | `block_rnn` | Recurrent neural network (LSTM/GRU) block architecture | Yes |
| Transformer | `transformer` | Standard transformer encoder-decoder for time series | Yes |
| TFT | `tft` | Temporal Fusion Transformer — interpretable multi-horizon forecasting | Yes |
| TiDE | `tide` | Time-series Dense Encoder — MLP-based with temporal features | Yes |
| TSMixer | `tsmixer` | All-MLP architecture mixing time and feature dimensions | Yes |

### Foundation Models (Pre-trained)

Zero-shot models pre-trained on large time series corpora. First run downloads weights from HuggingFace Hub.

| Model | ID | Description | GPU |
|-------|-----|-------------|-----|
| Chronos 2 | `chronos2` | Amazon's foundation model — tokenized time series with T5 architecture | Yes |
| TimesFM 2.5 | `timesfm` | Google DeepMind's 200M parameter foundation model, pre-trained on 100B+ data points | Yes |

---

## GPU Acceleration

21 models support GPU acceleration:
- **Apple Silicon (MPS)**: Detected automatically when running natively via `dev.sh`
- **NVIDIA CUDA**: Detected automatically on Linux with CUDA drivers
- **CPU fallback**: All GPU models work on CPU if no GPU is available

Docker Desktop on macOS cannot access Apple Silicon GPU. For GPU acceleration, run natively:
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install ".[torch]"
./dev.sh
```

### Soft Dependencies (Foundation Model Scorers)

MOMENT and Lag-Llama have pinned dependencies that conflict with the main environment. Install them separately when running natively:
```bash
pip install momentfm --no-deps
pip install lag-llama --no-deps  # or: pip install git+https://github.com/time-series-foundation-models/lag-llama.git
```

---

## Anomaly Detection Pipeline

Every model follows the same detection flow:

1. **Preprocessing**: infill missing values, apply smoothing, apply transforms (log, diff, standardize)
2. **Scoring**: model computes anomaly scores per timestamp per metric
3. **Detection**: quantile/threshold/IQR detector converts scores to binary anomalies
4. **Severity**: scores mapped to low/medium/high severity levels
5. **Regions**: consecutive anomaly points merged into anomaly regions
6. **Post-filtering**: persistence damping, minimum region size, volume gating

### Configurable Parameters

| Parameter | Description |
|-----------|-------------|
| `detector_type` | `quantile` (default), `threshold`, or `iqr` |
| `detector_threshold` | Sensitivity threshold (0.95 = top 5% flagged as anomalous) |
| `smoothing_window` | Pre-detection rolling mean (1 = no smoothing) |
| `transforms` | Chain of transforms: `log`, `diff`, `scale_standard` |
| `infill` | Missing value handling: `none`, `linear`, `time`, `ffill`, `zero` |
| `persistence_damping` | Suppress isolated false positives (0=off, 1=strong) |
| `min_anomaly_points` | Minimum region size to keep |
| `volume_gate_metric` | Suppress anomalies when a reference metric is below threshold |
