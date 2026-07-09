"""Check model compatibility with the user's current data configuration."""

from .registry import get_all_models
from ...models.schemas import ModelCompatibility


def check_compatibility(
    num_metrics: int,
    num_data_points: int,
    num_dimensions: int = 0,
    num_dimension_groups: int = 0,
) -> list[ModelCompatibility]:
    """Check all registered models against the given data configuration."""
    results = []
    for model in get_all_models():
        compatible = True
        reason = None

        if model.requires_dimensions and num_dimensions == 0:
            compatible = False
            reason = "Requires at least one dimension selected (e.g. NODE_NAME)."
        elif model.requires_dimensions and num_dimension_groups < 3:
            compatible = False
            reason = (
                f"Requires at least 3 peer groups. "
                f"Your dimension selection has {num_dimension_groups} groups."
            )
        elif not model.supports_multivariate and num_metrics > 1:
            compatible = False
            reason = (
                f"Univariate only — supports 1 metric at a time. "
                f"You have {num_metrics} metrics selected."
            )
        elif num_data_points < model.min_data_points:
            compatible = False
            reason = (
                f"Requires at least {model.min_data_points} data points. "
                f"Your data has {num_data_points}."
            )

        results.append(ModelCompatibility(
            model_id=model.id,
            compatible=compatible,
            reason=reason,
        ))

    return results
