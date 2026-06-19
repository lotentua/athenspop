# Travel Survey Genericity Checks

This note records the external survey families that should remain expressible with the same small source primitives before the generic library pivot is considered complete.

## Rule

The source package should not grow a survey-specific adapter because a known survey has different column names, code lists, weights, vehicle tables, geography, file formats, or publication artifacts.
Those transformations belong in examples or user code unless the same transformation is required by the Athens example and at least one independent survey example, or unless the primitive is low-effort, generic, realistic for future examples, and cheaper to maintain once in the library than repeatedly in examples.

## Evidence

- UK National Travel Survey through PAM: PAM's travel-survey-to-MATSim example reads household, person, and trip tables into pandas, renames source columns to shared diary concepts, maps activity and mode labels, loads a travel diary, and validates plans.
- US NHTS: FHWA describes NHTS as daily trips taken by households and individuals over a 24-hour period, including purpose, mode, travel time, time of day, and day of week: https://www.fhwa.dot.gov/policyinformation/nhts.cfm.
- US NHTS public data portal: the ORNL NHTS portal exposes current and historical downloadable products and describes daily non-commercial travel by all modes with traveler, household, and vehicle characteristics: https://nhts.ornl.gov/.
- France ENTD: INSEE describes the 2007-2008 National Transport and Travel Survey as a household-resident survey covering all journeys regardless of length, duration, mode, time of year, time of day, or purpose: https://www.insee.fr/en/metadonnees/source/serie/s1277.
- France EMP 2019: CASD describes the Individual Mobility Survey as covering about 20,000 metropolitan-France households, household vehicle equipment, and movements/travels for a selected individual, with consolidated trip distances: https://www.casd.eu/en/source/enquete-mobilite-des-personnes/.
- ActivitySim: ActivitySim examples and components use household, person, tour, and trip tables plus explicit scheduling models, probability tables, and time windows; AthensPop should mimic only the relevant mathematical and dataflow ideas, not the full framework or API.
- PopulationSim: PopulationSim is relevant for household/person table discipline, reproducible outputs, and validation posture, but its population synthesis controls and integerization algorithms are outside the AthensPop source scope.

## Acceptance Matrix

| Survey family | Expected example work | Source change allowed? |
|---|---|---|
| Athens | Convert the bundled wide diary source into canonical long-form dataframes, attach metadata, schedule times, impute study-specific return-home trips, build study-specific sequence labels, compute distances, cluster, and write artifacts. | Already covered by generic validation, scheduling, sequence, and clustering primitives. |
| UK NTS/PAM | Read source tables, map survey columns to `household_id`, `person_id`, `trip_id`, `trip_sequence`, `origin`, `destination`, `purpose`, `mode`, and timing columns, then reuse the same validation, scheduling, sequence, and clustering path. | No, unless the Athens example also needs the same primitive. |
| US NHTS | Read household/person/trip or vehicle-enriched tables, map NHTS identifiers and trip fields to canonical columns, keep weights and vehicle attributes as metadata, and define local purpose/mode grouping. | No, because weights, vehicle records, survey cycles, and NHTS codes are adapter/example concerns. |
| France ENTD/EMP | Read secured or public extracts outside the package, map household/person or selected-individual movement records to canonical trips, keep declared/consolidated distances and vehicle equipment as metadata, and define local purpose/mode grouping. | No, because access rules, French code lists, and distance-consolidation semantics are survey concerns. |
| ActivitySim-style examples | Use source primitives for tabular diaries, feasibility windows, stochastic repeated scheduling, and cluster analysis of generated or observed trips. | Yes only for generic scheduling, generation, random-seed, clustering, and diagnostics primitives that are also useful to Athens-shaped workflows. |
| PopulationSim-style examples | Use households and persons as metadata tables before or after an external synthesis workflow. | No, because population synthesis is not part of the AthensPop core. |

## Minimum Shared Core

The shared source core remains validation, scheduling, lean optional imputation only when it is generic, sequence construction, dissimilarity computation, clustering summaries, cut-tree data, and generic object-returning visualization where the same figure structure is realistic across examples.
The source should return Python objects such as pandas dataframes, immutable model objects, NumPy arrays, SciPy linkage matrices, Matplotlib figures, and plain containers.
The source should not read or write survey files, draw survey-specific figures, ship survey-code mappings, or know any default purpose and mode vocabulary.

## Review Checklist

- Can a new example start from three dataframes plus local mapping functions and reach a scheduled `SurveyDataset` without editing `src/athenspop`?
- Can the example keep source-specific columns such as weights, vehicles, regions, distances, or income bands as metadata without schema changes?
- Can the example define its own initial activity label and travel-state labeler without changing sequence code?
- Can the example compute cluster labels, cluster summaries, temporal state distributions, dendrogram layout, cut-tree nodes, and a generic Matplotlib dendrogram without survey-specific source code?
- If a requested source change is needed only by NHTS, EMP/ENTD, PAM, ActivitySim, or PopulationSim but not by Athens, can it stay in the example instead?
- If a helper is copied or semantically duplicated across two examples, or is clearly low-effort and generic enough for future examples, should it be extracted once into the source and tested there?
