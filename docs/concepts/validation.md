# Validation

Validation answers one question: can these dataframes be converted into trusted diary objects?

The validator checks table shape, required columns, key completeness, duplicate identifiers, joins between trips/persons/households, timing patterns, integer-second domains, trip order, and basic diary consistency.
It returns a report with errors and warnings instead of failing on the first issue.

Errors block model construction.
Warnings preserve model construction but flag data-quality or methodological concerns that a user should inspect.

The validator avoids noisy cascades.
When a row has a blocking key or timing error, later row-level checks skip that row where possible.
This keeps the report useful for non-experts because one bad value should not produce dozens of secondary messages.

Successful validation produces normalized dataframes that the internal model builder can trust.
