class StagePendingError(RuntimeError):
    """A milestone has not been implemented; never return a pretend result."""


def pending(stage: str, milestone: int) -> None:
    raise StagePendingError(
        f"{stage} is pending milestone {milestone}. "
        "This checkpoint provides scaffold, fixture validation, source discovery, and report preview."
    )
