# Deployment handoff

`render.yaml` is a schema-validated proposal for one Render web service, not an applied deployment. It selects the documented `1c-2g` compute plan and a 2 GB persistent disk. Confirm current hosting charges and the intended workspace before provisioning it.

Streamlit listens on the public service port; FastAPI listens only on loopback. Hosted mode requires a generated reviewer password. This is shared-password demo access, not multi-user production identity. The local default remains localhost-only without a password unless configured.

Run `python -m src.package_release` in the project environment to produce:

- `artifacts/release/customer-support-source.zip`: source, configuration, tests, notebooks, reports and documentation.
- `artifacts/release/model-bundle.zip`: completed DistilBERT checkpoint/tokenizer, metadata and trusted Logistic Regression artifact.
- `artifacts/release/manifest.json`: byte lengths and SHA-256 checksums.

Raw datasets, ticket databases, caches, training checkpoints, virtual environments and installers are excluded. Review dataset and upstream model terms before distributing weights; no bundle has been uploaded publicly.

## Publish

1. Source is pushed to [the GitHub repository](https://github.com/AbdulWahabMunir/Intelligent-Customer-Support-Ticket-Classification-Automated-Routing-Using-BERT). GitHub Actions runs tests and image builds.
2. Host `model-bundle.zip` at a downloadable HTTPS artifact URL you control. Use its exact checksum from the release manifest. Keep credentials and signed private URLs out of source.
3. Review the proposed Render resources, current cost and target workspace. No paid resource has been created.
4. Create a Blueprint from the repository. Provide `MODEL_BUNDLE_URL` and `MODEL_BUNDLE_SHA256` when prompted. Retrieve the generated dashboard password through Render's Environment page.
5. Verify login, ticket submission, feedback and restart persistence after the deployment finishes.

The bootstrap verifies the bundle checksum, rejects unsafe archive paths/symlinks, and checks for a completed checkpoint before starting services. Model files and SQLite data live under `/var/data`. A disk is available at runtime, not during builds. This single-instance disk design has deployment interruptions.

The proposed supervisor is verified locally with an isolated database. Schema validation does not establish a successful Render build. Linux Docker dependency installation and local container runtime tests passed. Remote bundle download and cloud runtime behavior remain unverified.

References: [compute plans](https://render.com/docs/compute-plans), [persistent disks](https://render.com/docs/disks), [Blueprint specification](https://render.com/docs/blueprint-spec).
