"""[GENERATED] watchlist 도메인 예외."""


class WatchlistError(Exception):
    pass


class IllegalTransition(WatchlistError):
    """방어선 A — 허용 안 된 전이."""

    def __init__(self, frm, to):
        self.frm = frm
        self.to = to
        super().__init__(f"불허 전이: {frm.name} -> {to.name}")


class InvariantViolation(WatchlistError):
    """방어선 B — 불변식 위반."""
