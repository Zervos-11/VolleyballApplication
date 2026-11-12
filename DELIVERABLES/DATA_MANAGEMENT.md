# Ethical, privacy and data-management record

This is the project's proposed operating procedure. It does not establish that any current video has permission, ethics clearance, an approved retention period or configured access controls. Complete the records with the supervisor and the institution's applicable requirements before treating an asset as cleared.

## Source and permitted use

For each video record its source URL, uploader/rights contact if known, acquisition date, original filename, parent match, SHA-256 and the evidence supporting the intended research use. Record separate scope for local analysis, showing frames in assessment, publishing labels, and redistributing footage. Public availability is not a permission record. An unresolved source remains pending and is excluded from the released research dataset.

Keep permission evidence in restricted storage and reference it by code in the manifest. Do not invent licence labels from a filename. Screen recordings for minors and other sensitive context; record the institutional decision where additional review or consent is required. No such decision is currently documented by this audit.

## Minimise identifiable data

Use player codes such as `home_p01` and annotator codes such as `ann01`. Do not need real names, contact details, face identification or a public jersey-to-name mapping for position evaluation. Pseudonymous trajectories and images should still be treated as potentially identifiable. Crop/redact spectators and identifying overlays in assessment illustrations where appropriate and permitted. Store any necessary identity key separately with restricted access.

Ball, pose, referee and audio annotation are outside the required Week 6 player-position scope. Do not collect further audio for this milestone. Existing WAV files are preserved pending review of their purpose and retention; this work does not delete source material.

## Storage and access

Record the project owner, authorised annotators/reviewers, primary storage location, backup location and access review date in the release log. Apply institution-approved access controls to raw video, consent records and identity keys. Use approved encrypted storage and backups where available; verify access rather than assuming a local folder is restricted. Keep secrets and permission documents out of public repositories.

Use immutable raw originals, separate derived files, and versioned annotation releases. Changes must record file, old/new value or revision reference, reason, contributor and timestamp. Never replace manual labels with a rerun of automatic tracking. Hash source videos using `Get-FileHash -Algorithm SHA256 -LiteralPath '<video path>'` and store the result in the manifest; hash released CSV/JSON artifacts as well. Do not place confidential permission text in a public manifest.

## Backup, retention and withdrawal

Proposed working schedule: back up after each annotation session to institution-approved storage; keep a separate weekly version; test restoration of one release before submission. Record actual backup and restoration dates. These actions have not been performed by the audit script.

The owner must record an approved retention end date and disposal method for raw video, derived labels, consent evidence and backups. The earlier document's blanket five-year retention claim is withdrawn because no project-specific policy was supplied. Do not automatically delete or publicly archive material on that basis.

If a source must be removed or permission changes, identify all derived clips, frames and labels through `source_group_id`, quarantine affected releases, record the reason and obtain the responsible institution's disposal instructions. Update the manifest and assessment counts without silently rewriting past release records.

## Release checklist to complete

- Source permission evidence and permitted-use scope recorded for every included video.
- Supervisor/institution review outcome, date and any conditions recorded.
- Privacy screening, access owners and any redaction decisions recorded.
- Backup/restore evidence and approved retention/disposal dates recorded.
- Dataset version, hashes, annotation contributors and change log recorded.
- Public/assessment artifacts checked against the recorded permitted-use scope.

All entries above are pending unless supported by an actual project record. No videos or labels were uploaded or shared by this work.
