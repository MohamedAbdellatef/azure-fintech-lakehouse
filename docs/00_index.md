# Documentation Index

| Version | Date       | Author             | Status |
| ------- | ---------- | ------------------ | ------ |
| 1.0     | 2026-03-04 | Mohamed Abdellatef | Final  |

> Central navigation page for all project design and implementation documents.

---

## 1) Recommended Reading Order

1. [Business Requirements (BRD)](./01-business-requirements.md)
2. [Project Overview](./02-project-overview.md)
3. [Data Dictionary](./03-data-dictionary.md)
4. [Data Quality Framework](./05-data-quality.md)
5. [Data Model (Star Schema)](./06-data-model.md)
6. [Source-to-Target Mapping](./04-source-to-target-mapping.md)
7. [Runbook](./07_runbook.md)

---

## 2) Document Map

| File | Purpose |
|---|---|
| [`01-business-requirements.md`](./01-business-requirements.md) | Business context, stakeholders, 18 questions, 13 KPIs, semantic rules, SLA/NFR scope |
| [`02-project-overview.md`](./02-project-overview.md) | End-to-end architecture flow, stack, layer contracts, status |
| [`03-data-dictionary.md`](./03-data-dictionary.md) | Bronze column contracts, Silver guarantees, Gold contract summary |
| [`04-source-to-target-mapping.md`](./04-source-to-target-mapping.md) | Column-level lineage and transformation logic from Bronze -> Silver -> Gold |
| [`05-data-quality.md`](./05-data-quality.md) | DQ rules, quarantine policy, monitoring outputs, dbt test plan |
| [`06-data-model.md`](./06-data-model.md) | Gold star schema: fact/dim design, SCD strategy, keys, traceability |
| [`07_runbook.md`](./07_runbook.md) | Operational run instructions (to be finalized after implementation) |

---

## 3) Diagrams

- [Architecture Diagram](./diagrams/architecture-diagram.png)
- [Source ERD](./diagrams/source-erd.png)
- [Gold Star Schema (Overview)](./diagrams/gold-star-schema.png)
- [Gold Star Schema (Detailed)](./diagrams/gold-star-schema-detailed.png)

---

## 4) Current Phase

- Current project state: **Design finalized, implementation in progress**.
- Locked design artifacts:
  - BRD
  - Data Model
  - Data Dictionary
  - Data Quality Framework
  - Source-to-Target Mapping
