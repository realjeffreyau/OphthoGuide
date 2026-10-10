# OphthoGuide source corpus

## Current source: National Eye Institute (NEI/NIH)

- Pages: `data/sources/nei_pages.csv`: 50 pages. nei_001–030 are the v1 condition, exam and anatomy pages. nei_031–050 (added 2026-10-08) are NEI subpages on treatment, diagnosis, causes and types, all `public_domain_verified`.
- Output: `data/processed/documents.jsonl`, per-page report in `data/processed/collection_report.md`
- Raw HTML cache: `data/raw/` (re-run with `--refresh` to refetch)

### Reuse permission

NEI copyright policy (https://www.nei.nih.gov/web-policies/copyright-policy), checked 2026-10-08:

> Unless otherwise noted, information on the National Eye Institute website is in the public domain.
> Public domain information may be freely distributed and copied, but, as a courtesy, we request that
> the National Eye Institute be given an appropriate acknowledgement.

> Most text appearing on NEI web pages was prepared by employees of the United States Government and
> therefore is not subject to copyright.

Graphics, photos, and illustrations are handled case by case, and some are copyrighted. Some linked
documents, such as journal articles, are also copyrighted.

**What we do:**
- Keep article **text only**. Drop images, figures, captions, embedded video and interactive graphics.
- Scan each article for third-party markers (`©`, "copyright", "used with permission", "reprinted",
  "all rights reserved", non-NEI "courtesy of"). If none are found, the page gets
  `reuse: "public_domain_verified"`. Otherwise it gets `needs_review` and is listed in the report.
- Credit every document with:
  `Courtesy: National Eye Institute, National Institutes of Health (NEI/NIH).`

## Sources considered and excluded from training text

| Source | Why excluded |
|---|---|
| AAO EyeSmart, Mayo Clinic, Cleveland Clinic, WebMD | Copyrighted. You can cite them as references, but don't copy them into the corpus. |
| MedlinePlus Medical Encyclopedia (A.D.A.M.) | Licensed content, not public domain. |

## Expansion path (30 → 60)

1. `data/sources/nei_expansion_candidates.csv` lists NEI subpages linked from v1 pages: treatment,
   surgery, diagnosis/testing, causes and types. These have the same structure, so the pipeline needs
   no changes. Append rows to `nei_pages.csv` and re-run.
2. **Imaging gap.** NEI has no dedicated page on eye imaging (OCT, fundus photography, fluorescein
   angiography). Candidates:
   - MedlinePlus **Health Topic** summaries (NLM-authored; public domain)
   - CDC Vision Health Initiative pages (public domain; check each page for third-party content)

   Both need their own extractor and a fresh reuse check.

## Expansion log
- **2026-10-08:** 30 → 50 pages. Added 20 pages from `nei_expansion_candidates.csv`: AREDS 2, wet AMD treatments, cataract surgery, cataract causes and types, cataracts and the eye, diabetic retinopathy injections and laser, dry eye causes and testing, glaucoma eye pressure, medicines, surgery and types, pink eye causes, treatment and newborns, types of refractive errors, refractive surgery (LASIK), and retinal detachment types and causes. Each page went through the same reuse scan and came back clean.
- **Known source disagreement:** pink eye duration. nei_008 (updated 2025-11-05) says "7 to 10 days"; nei_046 (updated 2019-06-26) says "1 to 2 weeks… sometimes 3 weeks or more" for viral pink eye. Answers should give both, with dates.


## Chat corpus expansion (2026-10-10)

`data/sources/nei_pages_chat.csv` lists the original 50 pages plus 22 NEI pages (nei_051–072).
- **Collected into:** `data/processed_chat/`. All 22 are `public_domain_verified`, and `validate_documents.py` passes.
- **Kept separate:** the frozen single-turn evaluation pins `data/processed/` and `scripts/retrieval.py` by hash, so the chat corpus lives beside them and the original corpus is unchanged.

**What was added:**
- **13 vetted candidates:** color blindness ×3, corneal ×3, glaucoma causes and treatment, living with low vision, eyeglasses, retinal-tear laser/freeze, retinal-detachment surgery, vitrectomy.
- **7 condition pages found on the NEI index:** blepharospasm, convergence insufficiency, Graves' eye disease, idiopathic intracranial hypertension, retinoblastoma, retinopathy of prematurity, Stargardt disease.
- **2 healthy-vision pages:** contact lenses; sports and eye safety.

**Gap that remains:** NEI has no page on screen-related eye strain or eye injuries in general. The likely addresses return 404, so those questions rely on related pages or on the AI's labelled general explanation.
