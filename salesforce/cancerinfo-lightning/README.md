# CancerInfo Explorer for Salesforce Lightning

A Lightning app and a **Home page tile** that call the public **CancerInfo API**
(`https://cancerinfo-api.onrender.com`) and show trusted, source-linked cancer information.

You choose a cancer from a type-ahead list that is loaded live from the API. Then you can type a
**question** or paste a **claim**. The result card is built from the sections the API actually returns.
**A card that has no data is never rendered.**

> Educational information only; not medical advice. CancerInfo API only retrieves passages; it has no AI.
> Claims are answered with related passages from trusted organisations and **no true/false verdict**.

Built for a **Developer Edition** org on **API version 67.0** (Summer '26). No flows were created, so
there are no flow tests. The Apex test class covers every Apex class.

---

## What's in the package

| Type | Name | Purpose |
|---|---|---|
| External Credential | `CancerInfo_API` | No-authentication credential with one Named Principal (`CancerInfoPrincipal`) |
| Named Credential | `CancerInfo_API` | Secured endpoint `https://cancerinfo-api.onrender.com`; Apex calls `callout:CancerInfo_API/...` |
| Apex class | `CancerInfoApiClient` | Read-only HTTP GET client with timeout, error mapping and JSON parsing |
| Apex class | `CancerInfoController` | `@AuraEnabled` methods: cancer list, profile header, section groups, question/claim evidence |
| Apex test | `CancerInfoControllerTest` | 22 tests with an in-memory `HttpCalloutMock`; no real callouts |
| LWC | `cancerInfoExplorer` | **The tile**, exposed to Home and App pages: mode toggle, type-ahead inputs, search |
| LWC | `cancerInfoProfile` | Result card that follows your mockup: header, main column, research/tools/sources side column |
| LWC | `cancerInfoBlock` | Renders one passage as paragraphs, bullets or symptom tiles, with source attribution |
| LWC | `cancerInfoTypeahead` | Accessible SLDS combobox with live, ranked suggestions |
| LWC | `cancerInfoUtils` | Shared helpers for filtering, question/claim suggestions and errors |
| FlexiPage | `CancerInfo_Explorer` | Full-width App Page that hosts the tile |
| Tab | `CancerInfo_Explorer` | Lightning Page tab |
| Lightning App | `CancerInfo` | Green-branded app (`#2E844A`) containing Home and CancerInfo Explorer |
| Permission Set | `CancerInfo_Access` | App, tab, Apex class and External Credential principal access (assign to admins) |

Every component is new and has a `CancerInfo` prefix. The package does **not** change any existing
profile, page, setting or record.

### How a search works

1. `getCancers` runs `GET /v1/cancers` and `GET /v1/coverage`. The cancer type-ahead matches names,
   aliases and anatomical sites, so "bowel" finds Colorectal Cancer and "leukemia" finds Leukaemia.
2. `getCancerProfile` runs `GET /v1/cancers/{slug}`. It returns the header and the list of display
   groups that have data.
3. `getSectionGroup` makes one call per group, in parallel, using `GET /v1/cancers/{slug}/{category}`.
   Cards appear as each group arrives. Empty groups are skipped.
4. If you typed a question or claim, `findEvidence` pulls out the keywords and maps them to topics
   (for example *lump* → symptoms). It then ranks matching passages from those topics, plus
   `GET /v1/search` filtered to the selected cancer, and highlights the related cards.

Question suggestions only offer topics that the selected cancer has data for. At the moment the API has
detailed content for 5 of its 25 cancers: ovarian, breast, colorectal, lung and prostate. The other 20
show a basic profile.

---

## Import into your Developer Edition org (Salesforce CLI)

All commands run from this folder (`salesforce/cancerinfo-lightning`). Steps 1–4 make **no changes**
to your org. Step 5 is the only step that writes metadata.

### 0. Prerequisites

- Salesforce CLI v2 (`sf --version`). VS Code with the Salesforce Extension Pack is optional.
- Sign in as a **System Administrator** of the Developer Edition org.

### 1. Connect the CLI to your org

```bash
sf org login web --alias cancerinfo-dev --instance-url https://login.salesforce.com
```

### 2. Confirm the org supports API 67.0

```bash
sf org display --target-org cancerinfo-dev
```

The `Api Version` shown must be **67.0 or higher**. Dev Edition orgs are on Winter '27 (68.0) or later
by now. If yours is lower, change `67.0` to your version in `sfdx-project.json`, in `manifest/*.xml`
and in every `*-meta.xml` file.

### 3. Preview what will be added (read-only)

```bash
sf project deploy preview --manifest manifest/package.xml --target-org cancerinfo-dev
```

Every row should be marked as **added**, not changed. A **conflict** or **changed** row means a
component with the same name already exists, so stop and check it.

### 4. Validate (check-only dry run with Apex tests, no changes)

```bash
sf project deploy validate --manifest manifest/package.xml --target-org cancerinfo-dev --test-level RunSpecifiedTests --tests CancerInfoControllerTest
```

Expected result: a successful status, all 22 tests passing, and over 75% code coverage. Note the
**Job ID** that is printed.

### 5. Import (this writes to the org)

Quick-deploy the job you just validated. This skips re-running the tests:

```bash
sf project deploy quick --job-id <JOB_ID_FROM_STEP_4> --target-org cancerinfo-dev
```

If the validation is more than 10 days old, deploy and test again instead:

```bash
sf project deploy start --manifest manifest/package.xml --target-org cancerinfo-dev --test-level RunSpecifiedTests --tests CancerInfoControllerTest
```

### 6. Grant access to System Administrators only

Assign the permission set to your own admin user:

```bash
sf org assign permset --name CancerInfo_Access --target-org cancerinfo-dev
```

To limit the app to the **System Administrator** profile in the UI, go to **Setup → App Manager →
CancerInfo → ▼ Edit → User Profiles**. Move *System Administrator* to **Selected Profiles** and click
**Save**. Assign `CancerInfo_Access` only to admin users. It holds the External Credential principal
access, and **callouts fail without it**, even for admins.

### 7. Smoke test

App Launcher → **CancerInfo** → **CancerInfo Explorer** tab. Then:

1. Type `bre`, choose **Breast Cancer** and click **Get Information**.
2. You should see the Overview, General Treatment Approaches, Symptoms (tiles) and Common Diagnostic &
   Staging Procedures cards, plus Related Tools and Trusted Sources.
3. Switch to **Check a claim**, type `Surgery is the only treatment` and click **Check Claim**. The
   *What Trusted Sources Say About This Claim* card appears.

> The API is hosted on a free tier that sleeps when idle, so the **first** request can take up to about
> a minute. If you see "did not respond in time", click **Retry**.

### 8. Add the tile to your Lightning Home page

1. Open the **Home** tab, click the **gear** icon and choose **Edit Page**. Lightning App Builder opens.
   If Home still uses the standard page, choose **Clone** or **New Home Page** when prompted.
2. In the left panel under **Custom**, drag **CancerInfo Explorer** into a **wide** region. In the
   narrow right column the results stack into one column, which also works.
3. Optionally set **Card title** in the property panel.
4. Click **Save**, then **Activate**. Under **App and Profile**, assign it to the app you use, such as
   Sales, together with **System Administrator**. This keeps it admin-only for now.

---

## Rollback (uninstall)

Before you remove the package:

1. Remove the tile from the Home page in Lightning App Builder.
2. Unassign the permission set: **Setup → Users → *you* → Permission Set Assignments → Edit**.

Then delete everything this package added. Nothing else is touched.

```bash
sf project deploy start --manifest manifest/package-empty.xml --post-destructive-changes manifest/destructiveChanges.xml --target-org cancerinfo-dev
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "We couldn't access the credential(s)…" or a callout permission error | Assign `CancerInfo_Access` to your user (step 6). |
| Deploy error on `ExternalCredential` (`NoAuthentication`) | Create it by hand: **Setup → Named Credentials → External Credentials → New**. Use label `CancerInfo API`, name `CancerInfo_API` and protocol **No Authentication**. Add the principal `CancerInfoPrincipal` (Named Principal, sequence 1). Then remove the `ExternalCredential` block from `manifest/package.xml` and repeat steps 4–5. |
| `Invalid API version` | Lower the API version as described in step 2. |
| Component not listed in App Builder | Hard-refresh the browser. The component targets **Home Page** and **App Page** only. |
| "No information was found for this request" | The cancer exists but the API has no published record for it yet. |

## Design notes

- **Current platform features:** LWC with `lwc:if`/`lwc:elseif`/`lwc:else`, `lwc:ref` and SLDS styling hooks
  (`--slds-c-*`, `--slds-g-*`); Apex `Assert` class; External Credential + Named Credential. No Aura, no
  Visualforce and no Remote Site Settings.
- **Security:** only GET requests, through a Named Credential. Slugs and categories are checked against an
  allowlist. Input is capped at 500 characters and URL-encoded. Only `http(s)` source links are rendered.
  All classes use `with sharing`. No data is stored in Salesforce.
- **Source licences:** every passage shows its organisation, link, update date and attribution text, as the
  sources' reuse conditions require. The API disclaimer appears in the footer.
- **Responsive:** results switch between one and two columns based on the tile's own width, using
  `ResizeObserver`, so the layout works in narrow Home page columns and on full-width pages.
