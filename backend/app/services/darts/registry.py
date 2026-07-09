"""
Darts model registry.

Defines all available anomaly detection models with metadata, parameter
definitions, and compatibility rules. This is the single source of truth
for both the backend runner and the frontend model cards.
"""

from ...models.schemas import ModelInfo, ModelParam
from ...models.enums import DartsModelId

MODEL_REGISTRY: dict[str, ModelInfo] = {}


def _register_models():
    """Register all available Darts models."""

    # --- Standalone Scorers ---

    MODEL_REGISTRY[DartsModelId.KMEANS] = ModelInfo(
        id=DartsModelId.KMEANS,
        name="KMeans Clustering",
        description=(
            "Groups sliding windows of the time series into clusters. "
            "Points far from any cluster center are scored as anomalous. "
            "Good for detecting unusual patterns and level shifts."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=50,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=3, max=100, step=1,
                description="Sliding window length for feature extraction",
            ),
            ModelParam(
                name="k", label="Clusters", type="int",
                default=8, min=2, max=50, step=1,
                description="Number of KMeans clusters",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.ISOLATION_FOREST] = ModelInfo(
        id=DartsModelId.ISOLATION_FOREST,
        name="Isolation Forest",
        description=(
            "Ensemble of random trees that isolate anomalies via fewer splits. "
            "Efficient for high-dimensional data and robust to irrelevant features."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_estimators", label="Trees", type="int",
                default=100, min=50, max=500, step=50,
                description="Number of isolation trees in the ensemble",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.LOF] = ModelInfo(
        id=DartsModelId.LOF,
        name="Local Outlier Factor",
        description=(
            "Density-based method that compares each point's local density "
            "to its neighbors. Detects anomalies in regions of varying density."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_neighbors", label="Neighbors", type="int",
                default=20, min=5, max=100, step=5,
                description="Number of neighbors for density estimation",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.ECOD] = ModelInfo(
        id=DartsModelId.ECOD,
        name="ECOD (Empirical CDF)",
        description=(
            "Uses empirical cumulative distribution functions to detect outliers. "
            "Parameter-free, fast, and interpretable."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.WASSERSTEIN] = ModelInfo(
        id=DartsModelId.WASSERSTEIN,
        name="Wasserstein Distance",
        description=(
            "Scores anomalies using the Earth Mover's Distance between "
            "distributions over sliding windows. Sensitive to distributional "
            "shifts rather than just point outliers."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=50,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=3, max=100, step=1,
                description="Sliding window length for distribution comparison",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.COPOD] = ModelInfo(
        id=DartsModelId.COPOD,
        name="COPOD (Copula)",
        description=(
            "Copula-Based Outlier Detection. Uses empirical copula models "
            "to capture dependencies between features. Parameter-free, fast, "
            "and handles high-dimensional data well."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.HBOS] = ModelInfo(
        id=DartsModelId.HBOS,
        name="HBOS (Histogram)",
        description=(
            "Histogram-Based Outlier Score. Builds histograms for each feature "
            "and scores points by inverse density. Extremely fast — suitable "
            "for large datasets where speed matters."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_bins", label="Histogram Bins", type="int",
                default=10, min=5, max=100, step=5,
                description="Number of bins for the histograms",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.KNN] = ModelInfo(
        id=DartsModelId.KNN,
        name="KNN Outlier",
        description=(
            "K-Nearest Neighbors outlier detection. Scores each point by its "
            "distance to the k-th nearest neighbor. Simple, intuitive, and "
            "effective for local density-based anomaly detection."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_neighbors", label="Neighbors", type="int",
                default=20, min=5, max=100, step=5,
                description="Number of nearest neighbors to consider",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.OCSVM] = ModelInfo(
        id=DartsModelId.OCSVM,
        name="One-Class SVM",
        description=(
            "One-Class Support Vector Machine. Learns a boundary around "
            "normal data in feature space. Points outside the boundary "
            "are anomalous. Effective for complex non-linear patterns."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="kernel", label="Kernel", type="select",
                default="rbf",
                options=["rbf", "linear", "poly", "sigmoid"],
                description="SVM kernel function (RBF works well for most cases)",
            ),
            ModelParam(
                name="contamination", label="Contamination (nu)", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies (maps to the nu parameter)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.INNE] = ModelInfo(
        id=DartsModelId.INNE,
        name="INNE",
        description=(
            "Isolation-based anomaly detection using Nearest-Neighbor Ensembles. "
            "Faster than Isolation Forest and less sensitive to parameter choices. "
            "A strong general-purpose detector."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_estimators", label="Estimators", type="int",
                default=200, min=50, max=500, step=50,
                description="Number of ensemble members",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.LODA] = ModelInfo(
        id=DartsModelId.LODA,
        name="LODA",
        description=(
            "Lightweight Online Detector of Anomalies. Uses an ensemble of "
            "random projections with histograms. Very fast, works well on "
            "high-dimensional data. Good for large datasets."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_bins", label="Bins", type="int",
                default=10, min=5, max=50, step=5,
                description="Number of histogram bins per projection",
            ),
            ModelParam(
                name="n_random_cuts", label="Random Cuts", type="int",
                default=100, min=10, max=500, step=10,
                description="Number of random projections",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.CBLOF] = ModelInfo(
        id=DartsModelId.CBLOF,
        name="CBLOF",
        description=(
            "Cluster-Based Local Outlier Factor. Clusters the data first, then "
            "scores each point based on its distance to the nearest large cluster. "
            "Effective for detecting points in small or sparse clusters."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_clusters", label="Clusters", type="int",
                default=8, min=2, max=20, step=1,
                description="Number of clusters",
            ),
            ModelParam(
                name="alpha", label="Alpha", type="float",
                default=0.9, min=0.5, max=1.0, step=0.05,
                description="Proportion of data belonging to large clusters",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.ROD] = ModelInfo(
        id=DartsModelId.ROD,
        name="ROD",
        description=(
            "Rotation-based Outlier Detection. Uses principal component analysis "
            "with random rotations. Robust to noisy and corrupted data. "
            "Parameter-free (no tuning needed beyond window size)."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.ABOD] = ModelInfo(
        id=DartsModelId.ABOD,
        name="ABOD",
        description=(
            "Angle-Based Outlier Detection. Measures the variance of angles "
            "between a point and all pairs of neighbours. Works well in "
            "high-dimensional spaces where distance-based methods degrade."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_neighbors", label="Neighbours", type="int",
                default=10, min=3, max=50, step=1,
                description="Number of neighbours for fast ABOD approximation",
            ),
            ModelParam(
                name="method", label="Method", type="select",
                default="fast",
                options=["fast", "default"],
                description="'fast' uses k-NN approximation (recommended); 'default' is exact but slow",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.SOS] = ModelInfo(
        id=DartsModelId.SOS,
        name="SOS",
        description=(
            "Stochastic Outlier Selection. Computes an affinity matrix and derives "
            "outlier probabilities based on how unlikely each point is to be selected "
            "by its neighbours. Good at finding outliers in regions of varying density."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="perplexity", label="Perplexity", type="float",
                default=4.5, min=1.0, max=50.0, step=0.5,
                description="Effective number of neighbours (similar to t-SNE perplexity)",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.LSCP] = ModelInfo(
        id=DartsModelId.LSCP,
        name="LSCP",
        description=(
            "Locally Selective Combination in Parallel. A meta-ensemble that "
            "combines LOF, Isolation Forest, and One-Class SVM, automatically "
            "selecting the best detector for each local region. More powerful "
            "than individual detectors but slower."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.SOD] = ModelInfo(
        id=DartsModelId.SOD,
        name="SOD",
        description=(
            "Subspace Outlier Detection. Finds outliers in axis-aligned subspaces "
            "rather than the full feature space. Effective for high-dimensional data "
            "where anomalies may only be visible in a few dimensions."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_neighbors", label="Neighbours", type="int",
                default=20, min=5, max=50, step=1,
                description="Number of neighbours for shared nearest neighbour graph",
            ),
            ModelParam(
                name="ref_set", label="Reference Set", type="int",
                default=10, min=2, max=30, step=1,
                description="Size of the reference set (must be < n_neighbors)",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.VAE] = ModelInfo(
        id=DartsModelId.VAE,
        name="VAE (Variational AE)",
        description=(
            "Variational Autoencoder — learns a probabilistic latent space of normal patterns. "
            "Anomaly score is the reconstruction probability. Captures complex non-linear "
            "relationships and provides uncertainty estimates."
        ),
        category="scorer",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=50,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=20, min=5, max=200, step=1,
                description="Sliding window length for feature extraction",
            ),
            ModelParam(
                name="epochs", label="Training Epochs", type="int",
                default=30, min=5, max=200, step=5,
                description="Number of training passes over the data",
            ),
            ModelParam(
                name="hidden_neurons", label="Hidden Layers", type="select",
                default="64,32,32,64",
                options=["32,16,16,32", "64,32,32,64", "128,64,32,64,128"],
                description="Comma-separated hidden layer sizes",
            ),
            ModelParam(
                name="latent_dim", label="Latent Dimension", type="int",
                default=2, min=1, max=16, step=1,
                description="Dimensionality of the latent space",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.PCA] = ModelInfo(
        id=DartsModelId.PCA,
        name="PCA Outlier",
        description=(
            "Principal Component Analysis outlier detection. Projects data onto principal "
            "components and uses the reconstruction error (sum of weighted projected distances) "
            "as anomaly score. Fast and effective for linear anomalies."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="n_components", label="Components", type="int",
                default=5, min=1, max=50, step=1,
                description="Number of principal components to retain (rest contribute to anomaly score)",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.MCD] = ModelInfo(
        id=DartsModelId.MCD,
        name="MCD (Min Covariance)",
        description=(
            "Minimum Covariance Determinant — robust estimation of the data's covariance matrix. "
            "Uses the Mahalanobis distance from the robust center as anomaly score. "
            "Effective for multivariate Gaussian-distributed data."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=10, min=1, max=100, step=1,
                description="Sliding window length",
            ),
            ModelParam(
                name="support_fraction", label="Support Fraction", type="float",
                default=0.5, min=0.1, max=1.0, step=0.05,
                description="Fraction of data used to compute robust covariance (lower = more robust)",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the data",
            ),
        ],
    )

    # --- Statistical ---

    MODEL_REGISTRY[DartsModelId.MODIFIED_ZSCORE] = ModelInfo(
        id=DartsModelId.MODIFIED_ZSCORE,
        name="Modified Z-Score",
        description=(
            "Uses median and MAD (median absolute deviation) instead of mean and "
            "standard deviation, making it robust to existing outliers. The simplest "
            "effective anomaly detector — near-instant with zero tuning. "
            "Score = 0.6745 × |x − median| / MAD."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=10,
        params=[
            ModelParam(
                name="threshold", label="Threshold", type="float",
                default=3.5, min=1.0, max=10.0, step=0.5,
                description="Modified Z-Score above which a point is flagged (3.5 is standard)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.STL_GESD] = ModelInfo(
        id=DartsModelId.STL_GESD,
        name="STL + GESD",
        description=(
            "Seasonal-Trend decomposition using LOESS (STL) followed by "
            "Generalized Extreme Studentized Deviate (GESD) outlier test on "
            "the residual component. The classic Twitter/X approach — ideal "
            "for strongly seasonal data. Decomposes the signal into trend, "
            "seasonal, and residual; anomalies are outliers in the residual."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=48,
        params=[
            ModelParam(
                name="period", label="Seasonal Period", type="int",
                default=24, min=2, max=365, step=1,
                description="Length of one seasonal cycle (e.g. 24 for hourly data with daily seasonality)",
            ),
            ModelParam(
                name="max_anomaly_pct", label="Max Anomaly %", type="float",
                default=0.10, min=0.01, max=0.50, step=0.01,
                description="Maximum fraction of points that GESD can flag as anomalous",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.SPECTRAL_RESIDUAL] = ModelInfo(
        id=DartsModelId.SPECTRAL_RESIDUAL,
        name="Spectral Residual",
        description=(
            "Microsoft's Spectral Residual method (used in Azure Anomaly Detector). "
            "Computes the FFT, extracts the spectral residual (deviation from the "
            "average log amplitude), and reconstructs a saliency map via inverse FFT. "
            "Points with high saliency are anomalous. Fast and effective for "
            "periodic signals with localized anomalies."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="spectral_window", label="Spectral Window", type="int",
                default=3, min=1, max=21, step=2,
                description="Averaging window in the frequency domain (odd number recommended)",
            ),
            ModelParam(
                name="score_window", label="Score Window", type="int",
                default=21, min=3, max=101, step=2,
                description="Smoothing window for the saliency scores (odd number recommended)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.CUSUM] = ModelInfo(
        id=DartsModelId.CUSUM,
        name="CUSUM",
        description=(
            "Cumulative Sum control chart. Tracks cumulative deviations from "
            "a reference mean. Detects subtle, sustained level shifts that "
            "point-based detectors miss. Classic method for process monitoring "
            "and telecom counter surveillance."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=20,
        params=[
            ModelParam(
                name="drift", label="Drift (k)", type="float",
                default=0.5, min=0.0, max=5.0, step=0.1,
                description="Allowable slack before accumulating deviation (in std devs)",
            ),
            ModelParam(
                name="threshold_h", label="Threshold (h)", type="float",
                default=5.0, min=1.0, max=20.0, step=0.5,
                description="Decision threshold for CUSUM statistic (in std devs)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.HAMPEL] = ModelInfo(
        id=DartsModelId.HAMPEL,
        name="Hampel Filter",
        description=(
            "Sliding-window median-based outlier detector. At each point, computes "
            "the local median and MAD (median absolute deviation). Points deviating "
            "more than a threshold from the median are anomalous. Very fast, robust, "
            "and requires minimal configuration."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=10,
        params=[
            ModelParam(
                name="window", label="Window Size", type="int",
                default=11, min=3, max=101, step=2,
                description="Sliding window size (odd number recommended)",
            ),
            ModelParam(
                name="n_sigma", label="Sigma Threshold", type="float",
                default=3.0, min=1.0, max=10.0, step=0.5,
                description="Number of MAD-scaled deviations to flag as anomalous",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.CHANGEPOINT] = ModelInfo(
        id=DartsModelId.CHANGEPOINT,
        name="Change Point Detection",
        description=(
            "Detects abrupt changes in the statistical properties of the signal "
            "using the PELT (Pruned Exact Linear Time) algorithm. Finds points "
            "where the mean or variance shifts. Useful for detecting regime changes "
            "in telecom counters. Uses the ruptures library."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=20,
        params=[
            ModelParam(
                name="model", label="Cost Model", type="select",
                default="rbf",
                options=["rbf", "l2", "l1", "normal"],
                description="Cost function: rbf (general), l2 (mean shift), l1 (median shift), normal (mean+variance)",
            ),
            ModelParam(
                name="penalty", label="Penalty", type="float",
                default=3.0, min=0.5, max=20.0, step=0.5,
                description="Higher penalty = fewer change points. Controls sensitivity.",
            ),
        ],
    )

    # --- Peer / Cohort Analysis ---

    MODEL_REGISTRY[DartsModelId.PEER_DIVERGENCE] = ModelInfo(
        id=DartsModelId.PEER_DIVERGENCE,
        name="Peer Divergence",
        description=(
            "Compares each group (e.g. each node) against the consensus of all peers. "
            "Flags groups whose behaviour diverges from the norm. Requires at least "
            "one dimension selected (e.g. NODE_NAME) with 3+ distinct values."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=10,
        requires_dimensions=True,
        params=[
            ModelParam(
                name="method", label="Consensus Method", type="select",
                default="median",
                options=["median", "mean"],
                description="How to compute the group consensus (median is more robust to outliers)",
            ),
            ModelParam(
                name="normalization", label="Score Normalization", type="select",
                default="pct",
                options=["pct", "mad", "zscore"],
                description=(
                    "How to normalize divergence scores. "
                    "'pct' = percentage deviation from consensus (most intuitive). "
                    "'mad' = MAD-normalized (how many median-absolute-deviations away). "
                    "'zscore' = standard-deviation normalized (z-score)."
                ),
            ),
            ModelParam(
                name="min_peers", label="Min Peers", type="int",
                default=3, min=2, max=100, step=1,
                description="Minimum number of peer groups required for comparison",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.PEER_PCA] = ModelInfo(
        id=DartsModelId.PEER_PCA,
        name="Peer PCA Reconstruction",
        description=(
            "Stacks all peer time series into a matrix and applies PCA. Nodes with high "
            "reconstruction error cannot be explained by the shared group behaviour and are "
            "flagged as anomalous. Catches structural differences invisible to pointwise comparison."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=10,
        requires_dimensions=True,
        params=[
            ModelParam(
                name="n_components", label="PCA Components", type="float",
                default=0.95, min=0.5, max=0.999, step=0.01,
                description="Variance ratio to retain (0.95 = keep components explaining 95% of variance)",
            ),
            ModelParam(
                name="min_peers", label="Min Peers", type="int",
                default=3, min=2, max=100, step=1,
                description="Minimum number of peer groups required",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.PEER_FUNCTIONAL_DEPTH] = ModelInfo(
        id=DartsModelId.PEER_FUNCTIONAL_DEPTH,
        name="Peer Functional Depth",
        description=(
            "Treats each node's time series as a curve and computes Modified Band Depth (MBD). "
            "The deepest curves are the most 'typical'; shallow curves lie outside the group "
            "envelope and are flagged. Catches nodes with atypical overall trajectory shape."
        ),
        category="scorer",
        supports_multivariate=False,
        min_data_points=10,
        requires_dimensions=True,
        params=[
            ModelParam(
                name="min_peers", label="Min Peers", type="int",
                default=3, min=2, max=100, step=1,
                description="Minimum number of peer groups required",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.PEER_FEATURE_ISOLATION] = ModelInfo(
        id=DartsModelId.PEER_FEATURE_ISOLATION,
        name="Peer Feature Isolation",
        description=(
            "Extracts statistical features per node (autocorrelation, entropy, trend, variance) "
            "and runs Isolation Forest to find nodes whose feature fingerprint is unusual. "
            "Detects lost periodicity, entropy shifts, and trend changes invisible to pointwise comparison."
        ),
        category="scorer",
        supports_multivariate=False,
        min_data_points=20,
        requires_dimensions=True,
        params=[
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.1, min=0.01, max=0.5, step=0.01,
                description="Expected proportion of anomalous nodes (0.1 = expect ~10% outliers)",
            ),
            ModelParam(
                name="min_peers", label="Min Peers", type="int",
                default=3, min=2, max=100, step=1,
                description="Minimum number of peer groups required",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.PEER_DTW_LOF] = ModelInfo(
        id=DartsModelId.PEER_DTW_LOF,
        name="Peer DTW + LOF",
        description=(
            "Computes Dynamic Time Warping distances between all peer time series, then applies "
            "Local Outlier Factor to find nodes whose shape is most different from neighbours. "
            "Catches time-shifted patterns that pointwise comparison misses. Requires dtaidistance."
        ),
        category="scorer",
        supports_multivariate=False,
        min_data_points=10,
        requires_dimensions=True,
        params=[
            ModelParam(
                name="dtw_window", label="DTW Window", type="int",
                default=10, min=1, max=100, step=1,
                description="Sakoe-Chiba band width (max warping in time steps). Smaller = faster but less flexible.",
            ),
            ModelParam(
                name="lof_neighbors", label="LOF Neighbors", type="int",
                default=3, min=1, max=20, step=1,
                description="Number of neighbours for Local Outlier Factor",
            ),
            ModelParam(
                name="min_peers", label="Min Peers", type="int",
                default=3, min=2, max=100, step=1,
                description="Minimum number of peer groups required",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.PEER_MATRIX_PROFILE] = ModelInfo(
        id=DartsModelId.PEER_MATRIX_PROFILE,
        name="Peer Matrix Profile",
        description=(
            "Uses STUMPY to compute the Matrix Profile distance (MPdist) between each node's "
            "time series and the peer consensus. Detects novel subsequence shapes that appear in "
            "one node but not in the group norm. Requires stumpy."
        ),
        category="scorer",
        supports_multivariate=False,
        min_data_points=50,
        requires_dimensions=True,
        params=[
            ModelParam(
                name="subsequence_length", label="Subsequence Length", type="int",
                default=24, min=4, max=200, step=1,
                description="Length of subsequences to compare (e.g. 24 for daily pattern at hourly resolution)",
            ),
            ModelParam(
                name="min_peers", label="Min Peers", type="int",
                default=3, min=2, max=100, step=1,
                description="Minimum number of peer groups required",
            ),
        ],
    )

    # --- Forecast-based models (local) ---

    MODEL_REGISTRY[DartsModelId.NAIVE_MEAN] = ModelInfo(
        id=DartsModelId.NAIVE_MEAN,
        name="Naive Mean",
        description=(
            "Simplest baseline — predicts the historical mean of the training data. "
            "Useful as a benchmark to ensure more complex models add value."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=10,
        params=[],
    )

    MODEL_REGISTRY[DartsModelId.EXPONENTIAL_SMOOTHING] = ModelInfo(
        id=DartsModelId.EXPONENTIAL_SMOOTHING,
        name="Exponential Smoothing",
        description=(
            "Classical forecasting with trend and seasonality components. "
            "Scores anomalies by comparing predictions to actual values. "
            "Best for data with clear seasonal patterns."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=48,
        requires_seasonality=True,
        params=[
            ModelParam(
                name="seasonal_periods", label="Seasonal Period", type="int",
                default=24, min=2, max=365, step=1,
                description="Length of one seasonal cycle (e.g. 24 for hourly data with daily pattern)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.FFT] = ModelInfo(
        id=DartsModelId.FFT,
        name="FFT (Spectral Analysis)",
        description=(
            "Fourier Transform decomposes the signal into frequency components "
            "and reconstructs using dominant frequencies. Residuals reveal anomalies. "
            "Best for strongly periodic signals."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=100,
        params=[
            ModelParam(
                name="nr_freqs_to_keep", label="Frequencies", type="int",
                default=10, min=1, max=100, step=1,
                description="Number of dominant frequencies to retain in reconstruction",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.THETA] = ModelInfo(
        id=DartsModelId.THETA,
        name="Theta Method",
        description=(
            "Decomposes the series into 'theta lines' capturing different curvatures. "
            "Good for trending data. Scores anomalies from forecast residuals."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="theta", label="Theta", type="float",
                default=2.0, min=0.0, max=10.0, step=0.5,
                description="Theta coefficient (0=linear, 2=standard)",
            ),
            ModelParam(
                name="season_mode", label="Seasonality", type="select",
                default="multiplicative",
                options=["multiplicative", "additive", "none"],
                description="How seasonality is modeled",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.ARIMA] = ModelInfo(
        id=DartsModelId.ARIMA,
        name="ARIMA",
        description=(
            "Auto-Regressive Integrated Moving Average. A classic statistical "
            "model for time series that captures trend, seasonality, and "
            "autocorrelation. Detects anomalies from forecast residuals."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="p", label="AR Order (p)", type="int",
                default=1, min=0, max=10, step=1,
                description="Number of autoregressive terms",
            ),
            ModelParam(
                name="d", label="Diff Order (d)", type="int",
                default=1, min=0, max=3, step=1,
                description="Number of differencing steps for stationarity",
            ),
            ModelParam(
                name="q", label="MA Order (q)", type="int",
                default=1, min=0, max=10, step=1,
                description="Number of moving average terms",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.AUTO_ARIMA] = ModelInfo(
        id=DartsModelId.AUTO_ARIMA,
        name="Auto ARIMA",
        description=(
            "Automatically selects optimal ARIMA (p, d, q) parameters using "
            "stepwise search. Handles seasonality detection. More robust than "
            "manual ARIMA but slower to fit."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="season_length", label="Seasonal Period", type="int",
                default=24, min=1, max=365, step=1,
                description="Length of one seasonal cycle (1 = no seasonality)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.FOUR_THETA] = ModelInfo(
        id=DartsModelId.FOUR_THETA,
        name="FourTheta",
        description=(
            "Enhanced Theta method that decomposes the series into four "
            "theta lines for richer curvature modeling. Often outperforms "
            "standard Theta on trending data."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="theta", label="Theta", type="float",
                default=2.0, min=0.0, max=10.0, step=0.5,
                description="Theta coefficient (0=linear, 2=standard)",
            ),
            ModelParam(
                name="season_mode", label="Seasonality", type="select",
                default="multiplicative",
                options=["multiplicative", "additive", "none"],
                description="How seasonality is modeled",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.NAIVE_SEASONAL] = ModelInfo(
        id=DartsModelId.NAIVE_SEASONAL,
        name="Naive Seasonal",
        description=(
            "Baseline model that repeats the last observed seasonal cycle. "
            "Useful as a benchmark. Deviations from the seasonal pattern "
            "indicate anomalies."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=10,
        params=[
            ModelParam(
                name="K", label="Seasonal Period", type="int",
                default=24, min=1, max=365, step=1,
                description="Length of one seasonal cycle (e.g. 24 for daily pattern in hourly data)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.NAIVE_DRIFT] = ModelInfo(
        id=DartsModelId.NAIVE_DRIFT,
        name="Naive Drift",
        description=(
            "Baseline model that extrapolates the linear drift from the "
            "training data. Simple but effective for detecting deviations "
            "from a trend."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=10,
        params=[],
    )

    MODEL_REGISTRY[DartsModelId.NAIVE_MOVING_AVG] = ModelInfo(
        id=DartsModelId.NAIVE_MOVING_AVG,
        name="Naive Moving Average",
        description=(
            "Baseline model that forecasts using the moving average of recent "
            "values. Anomalies are detected when values deviate from the "
            "running mean."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=10,
        params=[
            ModelParam(
                name="input_chunk_length", label="Window Size", type="int",
                default=24, min=2, max=200, step=1,
                description="Number of recent values to average",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.CROSTON] = ModelInfo(
        id=DartsModelId.CROSTON,
        name="Croston",
        description=(
            "Designed for intermittent demand / sparse time series. "
            "Separately models the demand size and the inter-arrival time. "
            "Best when values are often zero with occasional spikes."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=10,
        params=[
            ModelParam(
                name="version", label="Variant", type="select",
                default="classic",
                options=["classic", "optimized", "sba"],
                description="Croston variant (SBA = Syntetos-Boylan Approximation)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.PROPHET] = ModelInfo(
        id=DartsModelId.PROPHET,
        name="Prophet",
        description=(
            "Facebook's additive regression model with trend, seasonality, "
            "and holiday effects. Robust to missing data and trend changes. "
            "Widely used for business time series forecasting."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="growth", label="Growth", type="select",
                default="linear",
                options=["linear", "logistic", "flat"],
                description="Trend growth model (linear for trending data, flat for stationary)",
            ),
            ModelParam(
                name="changepoint_prior_scale", label="Changepoint Flexibility", type="float",
                default=0.05, min=0.001, max=0.5, step=0.01,
                description="Higher values allow more trend changes (more flexible fit)",
            ),
            ModelParam(
                name="seasonality_mode", label="Seasonality Mode", type="select",
                default="additive",
                options=["additive", "multiplicative"],
                description="Additive for constant-amplitude seasonality; multiplicative if seasonal effect scales with trend",
            ),
            ModelParam(
                name="seasonality_prior_scale", label="Seasonality Strength", type="float",
                default=10.0, min=0.01, max=50.0, step=1.0,
                description="Regularization strength for seasonality (higher = stronger seasonal patterns)",
            ),
            ModelParam(
                name="daily_seasonality", label="Daily Seasonality", type="select",
                default="auto",
                options=["auto", "true", "false"],
                description="Enable daily seasonality component (auto detects from data frequency)",
            ),
            ModelParam(
                name="weekly_seasonality", label="Weekly Seasonality", type="select",
                default="auto",
                options=["auto", "true", "false"],
                description="Enable weekly seasonality component",
            ),
            ModelParam(
                name="yearly_seasonality", label="Yearly Seasonality", type="select",
                default="auto",
                options=["auto", "true", "false"],
                description="Enable yearly seasonality component",
            ),
        ],
    )

    # --- Forecast-based models (global — support multivariate) ---

    MODEL_REGISTRY[DartsModelId.LINEAR_REGRESSION] = ModelInfo(
        id=DartsModelId.LINEAR_REGRESSION,
        name="Linear Regression",
        description=(
            "Uses lagged values as features for linear regression. "
            "Supports multivariate data and captures linear relationships "
            "across metrics. Fast training and interpretable."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="lags", label="Lag Window", type="int",
                default=24, min=2, max=200, step=1,
                description="Number of past values used as features",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.RANDOM_FOREST] = ModelInfo(
        id=DartsModelId.RANDOM_FOREST,
        name="Random Forest",
        description=(
            "Ensemble of decision trees using lagged values as features. "
            "Captures non-linear patterns and interactions across metrics. "
            "Robust to outliers in training data."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="lags", label="Lag Window", type="int",
                default=24, min=2, max=200, step=1,
                description="Number of past values used as features",
            ),
            ModelParam(
                name="n_estimators", label="Trees", type="int",
                default=100, min=10, max=500, step=10,
                description="Number of trees in the ensemble",
            ),
            ModelParam(
                name="max_depth", label="Max Depth", type="int",
                default=10, min=2, max=50, step=1,
                description="Maximum depth of each decision tree (deeper = more complex)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.LIGHTGBM] = ModelInfo(
        id=DartsModelId.LIGHTGBM,
        name="LightGBM",
        description=(
            "Fast gradient boosting using histogram-based learning. "
            "Efficient for large datasets. Supports multivariate via lagged features. "
            "Often the best out-of-the-box ML model for time series."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="lags", label="Lag Window", type="int",
                default=24, min=2, max=200, step=1,
                description="Number of past values used as features",
            ),
            ModelParam(
                name="n_estimators", label="Trees", type="int",
                default=100, min=10, max=1000, step=10,
                description="Number of boosting rounds",
            ),
            ModelParam(
                name="max_depth", label="Max Depth", type="int",
                default=6, min=2, max=20, step=1,
                description="Maximum depth of each tree (controls model complexity)",
            ),
            ModelParam(
                name="learning_rate", label="Learning Rate", type="float",
                default=0.1, min=0.01, max=1.0, step=0.01,
                description="Boosting learning rate (shrinkage — lower = more robust but slower)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.XGBOOST] = ModelInfo(
        id=DartsModelId.XGBOOST,
        name="XGBoost",
        description=(
            "Extreme Gradient Boosting — a scalable tree boosting system. "
            "Well-known for winning ML competitions. Captures non-linear "
            "patterns across metrics using lagged features."
        ),
        category="forecast",
        supports_multivariate=True,
        min_data_points=30,
        params=[
            ModelParam(
                name="lags", label="Lag Window", type="int",
                default=24, min=2, max=200, step=1,
                description="Number of past values used as features",
            ),
            ModelParam(
                name="n_estimators", label="Trees", type="int",
                default=100, min=10, max=1000, step=10,
                description="Number of boosting rounds",
            ),
            ModelParam(
                name="max_depth", label="Max Depth", type="int",
                default=6, min=2, max=20, step=1,
                description="Maximum depth of each tree (controls model complexity)",
            ),
            ModelParam(
                name="learning_rate", label="Learning Rate", type="float",
                default=0.1, min=0.01, max=1.0, step=0.01,
                description="Boosting learning rate (shrinkage — lower = more robust but slower)",
            ),
        ],
    )

    # --- Deep learning models (require PyTorch) ---

    _DL_COMMON_PARAMS = [
        ModelParam(
            name="input_chunk_length", label="Lookback Window", type="int",
            default=24, min=4, max=200, step=1,
            description="Number of past timesteps the model looks at for each prediction",
        ),
        ModelParam(
            name="n_epochs", label="Training Epochs", type="int",
            default=10, min=1, max=100, step=1,
            description="Number of training passes over the data (more = better fit but slower)",
        ),
        ModelParam(
            name="learning_rate", label="Learning Rate", type="float",
            default=0.001, min=0.0001, max=0.1, step=0.0001,
            description="Optimizer learning rate (lower = more stable but slower training)",
        ),
        ModelParam(
            name="batch_size", label="Batch Size", type="int",
            default=32, min=8, max=256, step=8,
            description="Number of samples per training batch",
        ),
        ModelParam(
            name="dropout", label="Dropout", type="float",
            default=0.1, min=0.0, max=0.5, step=0.05,
            description="Dropout rate for regularization (0 = no dropout)",
        ),
    ]

    MODEL_REGISTRY[DartsModelId.DLINEAR] = ModelInfo(
        id=DartsModelId.DLINEAR,
        name="DLinear",
        description=(
            "Decomposition-based linear model — decomposes the input into "
            "trend and remainder, then applies linear layers. Surprisingly "
            "competitive with complex models while being very fast to train."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=30,
        params=[*_DL_COMMON_PARAMS],
    )

    MODEL_REGISTRY[DartsModelId.NLINEAR] = ModelInfo(
        id=DartsModelId.NLINEAR,
        name="NLinear",
        description=(
            "Normalized linear model — subtracts the last value before "
            "applying a linear layer, avoiding distribution shift. "
            "Very fast and effective for non-stationary series."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=30,
        params=[*_DL_COMMON_PARAMS],
    )

    MODEL_REGISTRY[DartsModelId.NBEATS] = ModelInfo(
        id=DartsModelId.NBEATS,
        name="N-BEATS",
        description=(
            "Neural Basis Expansion Analysis — stacks of fully connected "
            "networks that learn interpretable basis functions for trend "
            "and seasonality. State-of-the-art pure DL forecaster."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=50,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="num_stacks", label="Stacks", type="int",
                default=10, min=2, max=30, step=1,
                description="Number of N-BEATS stacks (more = deeper model)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.NHITS] = ModelInfo(
        id=DartsModelId.NHITS,
        name="N-HiTS",
        description=(
            "Neural Hierarchical Interpolation for Time Series — extends "
            "N-BEATS with multi-rate sampling for efficient long-horizon "
            "forecasting. Faster and often more accurate than N-BEATS."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=50,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="num_stacks", label="Stacks", type="int",
                default=3, min=2, max=10, step=1,
                description="Number of N-HiTS stacks",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.TCN] = ModelInfo(
        id=DartsModelId.TCN,
        name="TCN (Temporal Conv)",
        description=(
            "Temporal Convolutional Network — uses dilated causal "
            "convolutions to capture long-range dependencies. "
            "Fast inference and parallelizable training."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=30,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="num_filters", label="Filters", type="int",
                default=3, min=1, max=32, step=1,
                description="Number of convolutional filters per layer",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.BLOCK_RNN] = ModelInfo(
        id=DartsModelId.BLOCK_RNN,
        name="Block RNN",
        description=(
            "Block-based Recurrent Neural Network (LSTM or GRU). "
            "Processes input in chunks and produces multi-step output. "
            "Good for capturing sequential patterns."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=30,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="rnn_model", label="RNN Type", type="select",
                default="LSTM",
                options=["LSTM", "GRU"],
                description="Recurrent cell type (LSTM has memory gates, GRU is simpler/faster)",
            ),
            ModelParam(
                name="hidden_dim", label="Hidden Size", type="int",
                default=25, min=8, max=128, step=1,
                description="Dimensionality of the recurrent hidden state",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.TRANSFORMER] = ModelInfo(
        id=DartsModelId.TRANSFORMER,
        name="Transformer",
        description=(
            "Attention-based model that captures long-range dependencies "
            "without recurrence. Uses self-attention to weigh the importance "
            "of different timesteps when making predictions."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=50,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="d_model", label="Model Dimension", type="int",
                default=16, min=8, max=128, step=8,
                description="Dimensionality of the transformer's internal representations",
            ),
            ModelParam(
                name="nhead", label="Attention Heads", type="int",
                default=4, min=1, max=16, step=1,
                description="Number of parallel attention heads (must divide model dimension)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.TFT] = ModelInfo(
        id=DartsModelId.TFT,
        name="Temporal Fusion Transformer",
        description=(
            "Google's interpretable multi-horizon forecasting model. "
            "Combines LSTM encoding with multi-head attention and variable "
            "selection. Excels on complex real-world datasets."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=50,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="hidden_size", label="Hidden Size", type="int",
                default=16, min=8, max=128, step=8,
                description="Size of the hidden layers throughout the model",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.TIDE] = ModelInfo(
        id=DartsModelId.TIDE,
        name="TiDE",
        description=(
            "Time-series Dense Encoder — a simple MLP-based architecture "
            "that encodes past values and decodes future predictions. "
            "Competitive with transformers at a fraction of the cost."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=30,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="hidden_size", label="Hidden Size", type="int",
                default=16, min=8, max=128, step=8,
                description="Size of the encoder/decoder hidden layers",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.TSMIXER] = ModelInfo(
        id=DartsModelId.TSMIXER,
        name="TSMixer",
        description=(
            "Time-Series Mixer — Google's MLP-Mixer adapted for time series. "
            "Alternates between time-mixing and feature-mixing layers. "
            "Strong multivariate performance with simple architecture."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=30,
        params=[
            *_DL_COMMON_PARAMS,
            ModelParam(
                name="hidden_size", label="Hidden Size", type="int",
                default=16, min=8, max=128, step=8,
                description="Size of the mixer hidden layers",
            ),
        ],
    )

    # --- Foundation models (pre-trained, HuggingFace Hub) ---

    _FOUNDATION_COMMON_PARAMS = [
        ModelParam(
            name="input_chunk_length", label="Context Window", type="int",
            default=64, min=8, max=512, step=8,
            description="Number of past timesteps the model uses as context for prediction",
        ),
    ]

    MODEL_REGISTRY[DartsModelId.CHRONOS2] = ModelInfo(
        id=DartsModelId.CHRONOS2,
        name="Chronos 2",
        description=(
            "Amazon's foundation model for time series forecasting. "
            "Pre-trained on large-scale data using a language-modeling approach. "
            "Zero-shot: no training needed on your data. Supports covariates. "
            "First run downloads model weights from HuggingFace Hub."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        foundation=True,
        min_data_points=100,
        params=[
            *_FOUNDATION_COMMON_PARAMS,
            ModelParam(
                name="hub_model_name", label="Model Variant", type="select",
                default="autogluon/chronos-2-small",
                options=[
                    "autogluon/chronos-2-small",
                    "amazon/chronos-2",
                    "autogluon/chronos-2-synth",
                ],
                description=(
                    "HuggingFace model variant: "
                    "small (28M params, fast), "
                    "default (120M params), "
                    "synth (120M, synthetic-data trained)"
                ),
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.TIMESFM] = ModelInfo(
        id=DartsModelId.TIMESFM,
        name="TimesFM 2.5",
        description=(
            "Google DeepMind's foundation model for time series. "
            "Pre-trained on 100B+ real-world time points. "
            "Zero-shot: no training needed. 200M parameters with "
            "up to 16K context length. "
            "First run downloads model weights from HuggingFace Hub."
        ),
        category="forecast",
        supports_multivariate=True,
        gpu_accelerated=True,
        foundation=True,
        min_data_points=100,
        params=[*_FOUNDATION_COMMON_PARAMS],
    )

    MODEL_REGISTRY[DartsModelId.TSPULSE] = ModelInfo(
        id=DartsModelId.TSPULSE,
        name="TSPulse (IBM Granite)",
        description=(
            "IBM's foundation model for time series anomaly detection. "
            "Combines time-domain and frequency-domain reconstruction to score anomalies. "
            "Pre-trained on diverse datasets — zero-shot, no training needed. "
            "Tiny model (1M params, ~4MB) runs efficiently on CPU. "
            "First run downloads weights from HuggingFace Hub."
        ),
        category="scorer",
        supports_multivariate=True,
        min_data_points=1536,
        gpu_accelerated=True,
        foundation=True,
        params=[
            ModelParam(
                name="scoring_mode", label="Scoring Mode", type="select",
                default="time+fft",
                options=["time+fft", "time", "fft"],
                description=(
                    "Anomaly scoring approach: "
                    "time+fft (default, best accuracy), "
                    "time (reconstruction error only), "
                    "fft (frequency analysis only)"
                ),
            ),
            ModelParam(
                name="aggregation_length", label="Aggregation Window", type="int",
                default=64, min=8, max=256, step=8,
                description="Window length for aggregating raw anomaly scores (higher = smoother)",
            ),
            ModelParam(
                name="smoothing_length", label="Smoothing Window", type="int",
                default=8, min=1, max=64, step=1,
                description="Post-aggregation smoothing window length",
            ),
        ],
    )

    # ── GPU-accelerated deep anomaly scorers ─────────────────────────────

    _DEEP_SCORER_COMMON_PARAMS = [
        ModelParam(
            name="window", label="Window Size", type="int",
            default=20, min=5, max=200, step=1,
            description="Sliding window length for feature extraction",
        ),
        ModelParam(
            name="epochs", label="Training Epochs", type="int",
            default=30, min=5, max=200, step=5,
            description="Number of training passes over the data",
        ),
    ]

    MODEL_REGISTRY[DartsModelId.DEEP_SVDD] = ModelInfo(
        id=DartsModelId.DEEP_SVDD,
        name="Deep SVDD",
        description=(
            "Deep Support Vector Data Description — learns a neural network "
            "mapping to a compact hypersphere. Points far from the sphere "
            "center score as anomalous. GPU-accelerated PyTorch model from PyOD."
        ),
        category="scorer",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=50,
        params=[
            *_DEEP_SCORER_COMMON_PARAMS,
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.05, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the training data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.AUTOENCODER] = ModelInfo(
        id=DartsModelId.AUTOENCODER,
        name="AutoEncoder (PyTorch)",
        description=(
            "Deep autoencoder trained to reconstruct normal patterns. "
            "High reconstruction error indicates anomalies. "
            "GPU-accelerated PyTorch implementation from PyOD."
        ),
        category="scorer",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=50,
        params=[
            *_DEEP_SCORER_COMMON_PARAMS,
            ModelParam(
                name="hidden_neurons", label="Hidden Layers", type="select",
                default="64,32,32,64",
                options=["32,16,16,32", "64,32,32,64", "128,64,32,64,128"],
                description="Comma-separated hidden layer sizes for the autoencoder",
            ),
            ModelParam(
                name="dropout_rate", label="Dropout", type="float",
                default=0.2, min=0.0, max=0.5, step=0.05,
                description="Dropout rate for regularization",
            ),
            ModelParam(
                name="contamination", label="Contamination", type="float",
                default=0.05, min=0.01, max=0.5, step=0.01,
                description="Expected fraction of anomalies in the training data",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.DAGMM] = ModelInfo(
        id=DartsModelId.DAGMM,
        name="DAGMM",
        description=(
            "Deep Autoencoding Gaussian Mixture Model — combines a deep autoencoder "
            "with a Gaussian mixture model. The compression network learns latent features "
            "while the estimation network predicts GMM membership probabilities. "
            "Anomaly score = negative log-likelihood under the learned mixture."
        ),
        category="scorer",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=100,
        params=[
            *_DEEP_SCORER_COMMON_PARAMS,
            ModelParam(
                name="hidden_dim", label="Hidden Dim", type="int",
                default=16, min=4, max=64, step=4,
                description="Latent dimension of the compression autoencoder",
            ),
            ModelParam(
                name="n_components", label="GMM Components", type="int",
                default=4, min=2, max=16, step=1,
                description="Number of Gaussian mixture components",
            ),
            ModelParam(
                name="lr", label="Learning Rate", type="float",
                default=0.001, min=0.0001, max=0.01, step=0.0001,
                description="Optimizer learning rate",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.ANOMALY_TRANSFORMER] = ModelInfo(
        id=DartsModelId.ANOMALY_TRANSFORMER,
        name="Anomaly Transformer",
        description=(
            "Transformer-based anomaly detection using Association Discrepancy. "
            "Computes KL divergence between learned series-associations (attention) "
            "and prior-associations (Gaussian kernel on temporal distance). "
            "Anomalies disrupt the expected temporal association pattern. "
            "State-of-the-art on many time series anomaly benchmarks (ICLR 2022)."
        ),
        category="scorer",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=100,
        params=[
            *_DEEP_SCORER_COMMON_PARAMS,
            ModelParam(
                name="d_model", label="Model Dimension", type="int",
                default=64, min=16, max=256, step=16,
                description="Transformer embedding dimension",
            ),
            ModelParam(
                name="n_heads", label="Attention Heads", type="int",
                default=4, min=1, max=8, step=1,
                description="Number of multi-head attention heads",
            ),
            ModelParam(
                name="n_layers", label="Encoder Layers", type="int",
                default=2, min=1, max=6, step=1,
                description="Number of transformer encoder layers",
            ),
            ModelParam(
                name="lr", label="Learning Rate", type="float",
                default=0.0001, min=0.00001, max=0.01, step=0.00001,
                description="Optimizer learning rate",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.TRANAD] = ModelInfo(
        id=DartsModelId.TRANAD,
        name="TranAD",
        description=(
            "Transformer-based adversarial anomaly detection with two-phase training. "
            "Phase 1: standard transformer reconstructs input windows. "
            "Phase 2: adversarial decoder amplifies anomaly reconstruction error. "
            "Sharpens the distinction between normal and anomalous points."
        ),
        category="scorer",
        supports_multivariate=True,
        gpu_accelerated=True,
        min_data_points=100,
        params=[
            *_DEEP_SCORER_COMMON_PARAMS,
            ModelParam(
                name="d_model", label="Model Dimension", type="int",
                default=64, min=16, max=256, step=16,
                description="Transformer model dimension",
            ),
            ModelParam(
                name="n_heads", label="Attention Heads", type="int",
                default=4, min=1, max=8, step=1,
                description="Number of multi-head attention heads",
            ),
            ModelParam(
                name="n_layers", label="Encoder Layers", type="int",
                default=2, min=1, max=6, step=1,
                description="Number of transformer encoder/decoder layers",
            ),
            ModelParam(
                name="lr", label="Learning Rate", type="float",
                default=0.0001, min=0.00001, max=0.01, step=0.00001,
                description="Optimizer learning rate",
            ),
        ],
    )

    # ── Foundation models (anomaly detection) ────────────────────────────

    MODEL_REGISTRY[DartsModelId.MOMENT] = ModelInfo(
        id=DartsModelId.MOMENT,
        name="MOMENT (CMU)",
        description=(
            "CMU's pre-trained time series foundation model for anomaly detection. "
            "Reconstructs input windows and scores based on reconstruction error. "
            "Zero-shot: no training needed on your data. "
            "First run downloads model weights from HuggingFace Hub."
        ),
        category="scorer",
        supports_multivariate=True,
        gpu_accelerated=True,
        foundation=True,
        min_data_points=512,
        params=[
            ModelParam(
                name="context_length", label="Context Length", type="int",
                default=512, min=64, max=512, step=64,
                description="Number of timesteps per reconstruction window",
            ),
            ModelParam(
                name="model_variant", label="Model Variant", type="select",
                default="AutonLab/MOMENT-1-large",
                options=[
                    "AutonLab/MOMENT-1-small",
                    "AutonLab/MOMENT-1-base",
                    "AutonLab/MOMENT-1-large",
                ],
                description="Model size: small (fastest), base, large (most accurate)",
            ),
        ],
    )

    MODEL_REGISTRY[DartsModelId.LAG_LLAMA] = ModelInfo(
        id=DartsModelId.LAG_LLAMA,
        name="Lag-Llama",
        description=(
            "Pre-trained probabilistic time series forecaster based on LLaMA architecture. "
            "Produces prediction intervals — anomalies are points where actuals fall "
            "far outside the predicted distribution. Zero-shot: no training needed. "
            "First run downloads model weights from HuggingFace Hub."
        ),
        category="scorer",
        supports_multivariate=False,
        gpu_accelerated=True,
        foundation=True,
        min_data_points=100,
        params=[
            ModelParam(
                name="context_length", label="Context Window", type="int",
                default=32, min=16, max=128, step=8,
                description="Number of past timesteps used as context",
            ),
            ModelParam(
                name="prediction_length", label="Prediction Horizon", type="int",
                default=1, min=1, max=24, step=1,
                description="Number of steps to predict forward for scoring",
            ),
            ModelParam(
                name="num_samples", label="Monte Carlo Samples", type="int",
                default=100, min=20, max=500, step=20,
                description="Number of probabilistic samples for prediction intervals",
            ),
        ],
    )


_register_models()


def get_all_models() -> list[ModelInfo]:
    return list(MODEL_REGISTRY.values())


def get_model(model_id: str) -> ModelInfo | None:
    return MODEL_REGISTRY.get(model_id)
