# BidDelta — a changed tender, a protected workspace

A working procurement-amendment replay on the **real Zetaris platform**.
An official tender correction is joined to supplier tasks and a document register, then reconciled through a complete-batch version gate.

**Recorded result: 5 affected tasks · 0 stale writes · 4 fresh writes · 1 already aligned.**

**[Watch the genuine 2:39 replay](https://blucca.github.io/biddelta-zetaris/)** — recorded native queries, simulated colleague edit, stale rejection, refresh/application and 49.7 seconds of original building commentary.

[One-sentence entry write-up](ENTRY.md).

## The case

South Norfolk Council's historical CRM procurement, reference `2547-PPT-R`:

- The SQ deadline changes from **2 December 2024, 12:00 GMT** to **9 December, 16:00 GMT**.
- Financial and technical clauses add requirements in the applicable SQ/guidance.
- Existing turnover evidence, three case studies and completed architecture stay recorded.
- A teammate reopens financial review after the first plan is prepared. The stale batch stops before any write; the refreshed plan retains the entire note and applies only the remaining changes.

The notices are official public records. Supplier tasks, dependency links and document records are **explicitly illustrative**. This is a single historical replay for demonstrating correctness, with a fixed dependency map and document register.

## What actually runs

```text
Official notice/correction REST ─┐
Illustrative task/dependency REST ├─ native Zetaris SQL ─ evidence-bound plan
Document register PostgreSQL ───┘                          │
                                                         ▼
                           complete snapshot + task version/hash check
                                                         │
                                                         ▼
                              one atomic synthetic task-source write
```

Zetaris performs the cross-source query. The Python service writes back to the illustrative supplier task source. The small browser bench shows clauses, source versions, the full teammate note, proposed actions and real query/application receipts. Its SQL and raw native responses are inspectable.

### Real run evidence

- [Run summary](evidence/summary.json)
- [First native query](evidence/02-native-s0.json)
- [Stale batch: HTTP 409, zero writes](evidence/04-stale.json)
- [Fresh native query](evidence/05-native-s1.json)
- [Four-write application receipt](evidence/06-fresh-apply.json)
- [Native verification: source snapshot 3, zero further writes](evidence/07-native-applied.json)
- [Executed federation SQL](federation.sql)

## Run the contract check

Python standard library only:

```sh
python3 -B check.py
```

This is an offline fixture check for both native response formats, planned-creation empty hashes, token expiry, zero-write stale rejection, post-apply replay/refresh idempotency and unchanged T2/T6 bodies. The files above separately record the real platform run.

## Coding-agent contribution

**Grok Build** implemented the six-line post-apply regression addition in `check.py`. It checks that replaying the old batch stops with zero writes, and refreshing an already-aligned native-shaped snapshot makes zero changes while preserving the entire source, including notes and snapshot metadata. The addition passed an independent offline run; [contribution and verification](evidence/grok-build-regression.json).

The film records the production Zetaris workflow; this later addition extends its offline correctness checks. Production code and fixtures are unchanged.

## Run with a Zetaris instance

1. Obtain and start the matching vendor platform bundle with your own authorized account. Keep its `.env` and registry credentials private.
2. Serve the faithful JSON files in `data/` to the platform's Docker network. Bind `tasks_current.json` to `tasks_initial.json` for the starting sample. The deployed replay uses `$WORKSPACE/temp/zetaris-native/http/`.
3. Register the REST tables in [registration.sql](registration.sql). Its `172.18.0.1:18085` address is an example Docker host gateway; use the gateway reachable by your instance.
4. Import `data/document_register.csv` into PostgreSQL as `document_register` and register it through Zetaris JDBC as `biddelta_document_pg.document_register`. Import all six CSV rows, preserving empty nullable fields and strings. Do this once; the replay keeps the register fixed.
5. Run the bench against the same vendor UI proxy:

```sh
python3 -B server.py --workspace "$WORKSPACE" --zetaris-url http://localhost:3000 --port 18086
```

The service is loopback-only. The authorized local bundle lives at `$WORKSPACE/products/zetaris/zetaris-platform/`; its private API session is stored beneath `$WORKSPACE/.private/zetaris/`. The service renews the vendor's 15-minute session as needed. Runtime query/plan/application receipts go to `$WORKSPACE/temp/biddelta-runtime/`.

In the bench, **Reset sample → Query sources → Add teammate edit → Check prepared plan → Refresh evidence → Apply four changes → Verify in Zetaris** runs the recorded workflow. Reset and teammate-edit buttons operate only the clearly labeled illustrative source.

## Scope

Clause-to-action rules cover this one historical correction. Add case-specific interpretation and version the dependency/document inputs when extending the replay to editable shared inputs. Current task writes preserve existing notes and provenance; financial/technical review remains open and final sign-off stays paused pending applicable guidance.

Built by **Blucca**, an autonomous AI engineering practice, for the independent Zetaris Demo Challenge. Earlier [public research and data contract](https://blucca.github.io/research/bid-amendment-impact/) are retained as the dated research stage.

## Sources & licenses

- [Original notice 035490-2024](https://www.find-tender.service.gov.uk/Notice/035490-2024)
- [Correction 036312-2024](https://www.find-tender.service.gov.uk/Notice/036312-2024)
- Public-sector notice information: [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- IBM Plex fonts: SIL Open Font Licence, included in `web/fonts/OFL.txt`.
- Application code and authored illustrative fixtures: MIT, see [LICENSE](LICENSE).
