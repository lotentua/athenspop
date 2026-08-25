# Model API

Model objects represent validated tables as immutable diaries, trips, time windows, and optional respondent and household metadata. Construct `SurveyDataset` through `from_dataframes` unless a caller already owns the trusted-object boundary.

```{eval-rst}
.. automodule:: athenspop.model.survey
   :members: Diary, HouseholdMetadata, PersonMetadata, SurveyDataset,
      TimeWindow, Trip
```
