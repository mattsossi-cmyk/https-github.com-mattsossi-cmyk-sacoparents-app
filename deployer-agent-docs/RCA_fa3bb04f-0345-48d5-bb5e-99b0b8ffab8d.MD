# Information Request: MongoDB Atlas Backup Retention

## Question
For the production deployment (align-report, live at https://sacoparentsalign.com), what is the automated backup/snapshot retention period (in days) for the Emergent-provided production MongoDB Atlas database, and the maximum time a deleted document may persist in backups?

## Finding
This figure is **NOT determinable or configurable from the deployer agent's side**.

- None of the deployer agent's tools expose MongoDB Atlas backup configuration: snapshot schedule, retention window, or point-in-time-restore (PITR) window.
- The only DB access available is a read-only query against live collection data (mongo_query); it does not read Atlas cluster-level backup policy.
- Atlas backup/retention policy is platform infrastructure managed by Emergent. It is not surfaced to this agent and cannot be changed by the user or by app source code.

## Conclusion
I cannot provide a verified number of days, and I am explicitly declining to estimate (per the request). The authoritative retention figure — both the snapshot retention window and the maximum time a deleted document can persist in backups — must be obtained from Emergent support, which owns the Atlas infrastructure.
