# scrapper-search

## Overview

scrapper-search is maintained as a production-ready release copy generated from the SANDBOX workspace.

## Repository role

- Bucket: `services`
- Project kind: `node-service`
- Release strategy: `github-release-source-zip`
- Owner target: `iaguu`
- Notes: Personal or independent release repository maintained under the iaguu account.

## Technology stack

Node.js, npm

## Quality gates

- CI workflow: `.github/workflows/ci.yml`
- Release workflow: `.github/workflows/release.yml`
- Production hygiene validation: `D:\Projetos\SCRIPTS\verify-production-builds.ps1`

## Local setup

```bash
npm install
```

## Validation and build

```bash
npm run build --if-present
npm test --if-present
```

## Release process

1. Develop and validate in `D:\Projetos\SANDBOX`.
2. Sync the clean release copy into `D:\Projetos\PRODUCTION\services\scrapper-search`.
3. Run CI and local validation.
4. Create or update the GitHub repository for this project.
5. Publish tagged releases through GitHub Actions.

## Source of truth

The development source of truth for this project lives in:

`D:\Projetos\SANDBOX\services\scrapper-search`
