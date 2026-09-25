"""Fixed-time traffic-signal delay baseline."""

import random


def fixed_time_delay_penalty(
	num_intersections_on_route: int,
	seed: int | None = None,
) -> float:
	"""Estimate extra signal delay without emergency preemption."""
	if num_intersections_on_route < 0:
		raise ValueError("num_intersections_on_route must be non-negative")

	rng = random.Random(seed)
	delay = 0.0
	for _ in range(num_intersections_on_route):
		if rng.random() < 0.5:
			delay += rng.uniform(10, 30)
	return delay
