import math


def lttb_downsample(
    timestamps: list[str],
    values: list[float | None],
    target_points: int,
) -> tuple[list[str], list[float | None]]:
    """
    Largest Triangle Three Buckets (LTTB) downsampling.
    Preserves the visual shape of the time series while reducing point count.

    Returns (downsampled_timestamps, downsampled_values).
    """
    n = len(values)
    if n <= target_points:
        return timestamps, values

    # Filter out None values for the algorithm, but track their positions
    # For LTTB we need numeric values, so we'll use forward-fill for Nones
    filled_values = []
    last_valid = 0.0
    for v in values:
        if v is not None:
            last_valid = v
        filled_values.append(last_valid)

    # Always keep first and last points
    sampled_indices = [0]

    bucket_size = (n - 2) / (target_points - 2)

    a = 0  # Index of previously selected point

    for i in range(1, target_points - 1):
        # Calculate bucket boundaries
        bucket_start = int(math.floor((i - 1) * bucket_size)) + 1
        bucket_end = int(math.floor(i * bucket_size)) + 1
        bucket_end = min(bucket_end, n - 1)

        # Calculate next bucket average
        next_bucket_start = int(math.floor(i * bucket_size)) + 1
        next_bucket_end = int(math.floor((i + 1) * bucket_size)) + 1
        next_bucket_end = min(next_bucket_end, n)

        avg_x = 0.0
        avg_y = 0.0
        count = next_bucket_end - next_bucket_start
        if count > 0:
            for j in range(next_bucket_start, next_bucket_end):
                avg_x += j
                avg_y += filled_values[j]
            avg_x /= count
            avg_y /= count

        # Find point in current bucket with largest triangle area
        max_area = -1.0
        max_idx = bucket_start

        point_a_x = a
        point_a_y = filled_values[a]

        for j in range(bucket_start, bucket_end + 1):
            if j >= n:
                break
            # Triangle area formula (simplified: 2x area, no need for actual area)
            area = abs(
                (point_a_x - avg_x) * (filled_values[j] - point_a_y)
                - (point_a_x - j) * (avg_y - point_a_y)
            )
            if area > max_area:
                max_area = area
                max_idx = j

        sampled_indices.append(max_idx)
        a = max_idx

    # Always include last point
    sampled_indices.append(n - 1)

    result_ts = [timestamps[i] for i in sampled_indices]
    result_vals = [values[i] for i in sampled_indices]

    return result_ts, result_vals


def lttb_downsample_band(
    timestamps: list[str],
    lower: list[float | None],
    upper: list[float | None],
    target_points: int,
) -> tuple[list[str], list[float | None], list[float | None]]:
    """
    LTTB downsample a band (lower + upper) synchronously.
    Uses midpoint for triangle selection, then picks both lower and upper at those indices.
    """
    n = len(timestamps)
    if n <= target_points:
        return timestamps, lower, upper

    # Run LTTB on midpoint to get sampled indices
    midpoints = [
        ((lo or 0) + (hi or 0)) / 2
        for lo, hi in zip(lower, upper)
    ]
    sampled_ts, _ = lttb_downsample(timestamps, midpoints, target_points)

    # Map timestamps back to indices
    ts_to_idx = {t: i for i, t in enumerate(timestamps)}
    indices = [ts_to_idx[t] for t in sampled_ts]

    return (
        sampled_ts,
        [lower[i] for i in indices],
        [upper[i] for i in indices],
    )
