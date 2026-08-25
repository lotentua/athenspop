# Model API

The model layer contains the immutable objects used after dataframe validation: trips, diaries, timing windows, metadata, and the complete survey dataset.

Construct a dataset with {py:meth}`athenspop.model.survey.SurveyDataset.from_dataframes` unless your application already owns a trusted object boundary. See [Data model and validation](../concepts/data_model.md) for the relationship between input tables and these objects.

```{eval-rst}
.. automodule:: athenspop.model.survey
   :members: Diary, HouseholdMetadata, Metadata, MetadataValue, PersonMetadata,
      SurveyDataset, TimeWindow, Trip

.. automodule:: athenspop.schema
   :members: TimingPattern

.. automodule:: athenspop.types
   :members: DissimilarityMatrix, TravelTimeFunction
```
