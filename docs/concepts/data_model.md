# Data Model

`athenspop` starts from three tables: `trips`, optional `persons`, and optional `households`.

The dataframe boundary is intentionally explicit. Users provide conventional columns, validation reports all independent schema and domain issues, and the internal model is built only after hard errors are resolved.

The internal model is a collection of diaries. Each diary belongs to one person, contains ordered trips, and may carry person and household metadata. Internal functions assume those model objects are complete and trusted; expensive validation stays at the file and dataframe boundary.

All model time values are integer seconds from a documented `t0`. Clock strings, civil timestamps, and timedeltas are boundary concerns, not internal model values.

The main public model objects are `SurveyDataset`, `Diary`, `Trip`, `TimeWindow`, `PersonMetadata`, and `HouseholdMetadata`.
