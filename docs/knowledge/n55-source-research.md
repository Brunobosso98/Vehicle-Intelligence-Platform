# N55 source research

Research date: 2026-10-15. Vehicle: BMW 335i F30 2015 / N55.
This is a research checkpoint; corpus ingestion and Phase 8 acceptance remain incomplete.
The [source manifest](n55-source-manifest.json) records actual publisher, canonical URL,
retrieval timestamp, checksum, trust, applicability, redistribution and ingestion status.
Unknown publication dates and versions remain null.

## Sources considered and acquired

| Source (canonical URL in manifest) | Publisher / trust | Scope and current decision |
| --- | --- | --- |
| F30 introduction, T0122601EN | BMW Group / Tier 1 | F30/N55 architecture, published 2011-10-14. Select N55 sections; exclude N20/chassis content. |
| 2011 coupe/convertible introduction, T0076954EN_US | BMW Group / Tier 1 | Original N55 architecture, charge-air and thermal explanation, published 2010-01-16. Earlier platform hardware is not proof of 2015 F30 fitment. |
| Gasoline direct injection | Bosch Mobility / Tier 1 | Generic fuel supply, management, ignition and sensing; modern component limits are not N55 targets. |
| High-pressure pump HDP | Bosch Mobility / Tier 1 | Generic demand-related pressure principles. Exact installed N55 pump identity unverified. |
| N55 Super License | MHD Tuning / Tier 2 | Vendor/PWG/EWG/fuel/stage context. Conflicting hardware sections must be flagged. |
| N55-EWG CustomROM | protuningfreaks / Tier 2 | Vendor/EWG-specific calibration and fuel context, published 2021-05-12. User ROM identity unknown. |
| How To Datalog | protuningfreaks / Tier 2 | Vendor logging context; does not establish current collector or recorded signal availability. |
| SI B17 01 15, February 2015 | BMW of North America / Tier 1, official NHTSA archive | Cooling repair context on N55/F30 with option 0337, produced to July 2014. Unknown production/package identity remains partial; not a model-year cutoff. |

Seven public HTML sources and one official-regulator-hosted BMW PDF were acquired through the
controlled URL boundary. Reviewed selections reconstruct ten logical document versions/twenty
chunks locally; real embedding/index activation and sixty-query retrieval passed on October 15–16.
The reviewed October 16 bootmod3 metadata revision records EWG as a hardware requirement;
it does not establish that the vehicle has that wastegate. Raw originals stay in ignored
`.knowledge/raw/`. No full source is committed. Dynamic page changes require checksum review.

The [BMW cooling bulletin](https://static.nhtsa.gov/odi/tsbs/2015/MC-10147075-9999.pdf) is selected
only through page 1 subject/model/situation/cause, before the procedure. Its package and production
conditions are preserved. Diagrams, hose-routing repairs and warranty content are excluded from
selection. Public NHTSA hosting does not remove BMW copyright. Publication is February 2015; no
exact publication day is invented.

## Rejected or unavailable

- Official ST916 N55 training PDF: search found an indexed record, but direct browser fetch
  returned 404 and controlled acquisition failed. No stored checksum or ingestion is claimed.
- Third-party ST916 mirrors: not accepted as verified original acquisition. Mirrored copyright
  notices restrict copying/transfer. No whole manual is committed.
- N20 training documentation: cannot support normative N55 claims.
- BMW article T0129152EN: rejected because displayed engine text describes an earlier twin-turbo
  arrangement; a publication/site label alone does not establish N55 relevance.
- Forum/Reddit universal Stage 2 pressure anecdotes: excluded from authoritative ingestion.
  Community-like content is only a clearly synthetic adversarial fixture.
- Unidentified upgraded pump/intercooler/turbo product pages: part applicability cannot be
  established without recorded manufacturer and exact part identity.

## Stage 2 / Calibration Applicability

Stage 2 is not universal. Official MHD and bootmod3 sources describe their own maps, hardware
and fuels. Neither identifies the user's actual tuner, installed map revision, PWG/EWG hardware,
fuel or upgraded pump. Read those from recorded historical configuration; unknown values remain
UNKNOWN/PARTIAL. OEM principles do not become exact tuned pressure/boost/timing/torque targets.

The acquired MHD page contains a concrete conflict: its main feature description and later
Stage 2 Maps block list different hardware prerequisites. Preserve both source locations and
surface the disagreement; do not silently select one as a universal requirement. PWG/EWG and
fuel variants must also remain distinct. Date/version is unknown for this dynamic page.

Safe claims cite applicable architecture and explicitly preserve unknown map applicability.
Unsafe claims invent any universal target from a stage label or apply another vendor's map.
The application exposes no vehicle control/flashing instructions even when vendor pages contain them.

## HPFP interpretation

Bosch's generic references do not establish N55 operating targets or installed pump identity.
Interpret actual/commanded pressure only with recorded RPM, load, throttle, boost, fuel, effective
calibration and historical baseline. Source operating conditions and applicability remain attached.
Missing tune-specific targets are a documentary gap. A static number never establishes failed
HPFP, and missing documentation cannot be solved by a LoggingRecipe. Recorded commands remain
separately attributed vehicle facts.

## Coverage, licensing and reconstruction

Candidates cover N55 architecture/air/thermal principles, generic GDI management/sensing/ignition
and vendor calibration/logging concepts. Detailed 2015 DME strategy, variant-specific wastegate
control, oil/cooling service limits, complete diagnostic procedures, exact hardware and tune targets remain
incomplete. Continue official-source research instead of filling gaps from model memory.

Public access does not grant redistribution. Raw pages/extraction remain local and gitignored;
commit metadata and project-authored fixtures. Download configured manifest URLs through the
bounded acquisition boundary, compare checksums, review changed content/applicability/conflicts,
and create immutable versions. The controlled candidate/review CLI supports acquisition and
metadata-only corrections. A real metadata refresh reused every embedding and passed retrieval.
See [ingestion](../runbooks/knowledge-ingestion.md) and [refresh](../runbooks/knowledge-refresh.md).
Image-only diagrams and ambiguous tables cannot establish invented text or numeric specifications.

## Additional primary-source review — 2026-10-16

Two additional publisher pages were acquired through the controlled downloader and reviewed
against exact raw checksums. The expanded local index has ten sources, twelve documentary
selections and twenty-three chunks. The three new chunks were embedded in one explicitly
authorized call; all previous vectors were reused. Sixty real-vector retrieval cases still pass.

| Candidate | Publisher / proposed trust | Useful scope and explicit limits | Rights/status |
| --- | --- | --- | --- |
| [Electronic engine control unit](https://www.bosch-mobility.com/en/solutions/control-units/engine-control-unit/) | Bosch Mobility / Tier 2 technical principles | Generic fuel, air, injection, ignition and torque arbitration. Selected opening description and first operating-principle paragraph (HTML sections 1/7, paragraph 0). Modern platform features do not identify the installed N55 DME, firmware or stock/tuned targets. Flashing/control passages are excluded. | Publisher copyright; local storage/metadata only; publication date unavailable; selected/indexed locally. |
| [Wastegate turbochargers for gasoline engines](https://www.garrettmotion.com/turbocharger-technology/gasoline-turbochargers/wastegate-turbochargers-for-gasoline-engines/) | Garrett Motion / Tier 2 technical principles | Generic electric bypass-valve boost regulation and water-cooled construction (HTML section 4, paragraph 1). No proof that the actual N55 turbo is a Garrett product; no vehicle-specific wastegate, boost or thermal target. Marketing percentages are excluded. | Publisher copyright; local storage/metadata only; publication date unavailable; selected/indexed locally. |

EWG describes an electronic wastegate hardware configuration. It must not be treated as an engine
code variant or inferred for this car solely from the model year. The bootmod3 source version 2
records the EWG hardware requirement; unknown actual wastegate identity remains partial.
