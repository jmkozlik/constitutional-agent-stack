# Health and Consumer-Wellness Money Plays from 2025–2026 US Policy Openings (as of Oct 9, 2026)

Method note: research was done Oct 9, 2026, with about 17 searches. Firecrawl was rate-limited (HTTP 429), so most results came from WebSearch summaries of the pages, not full-page fetches. Treat figures marked "secondary" or "estimate" with caution. The policy facts come from the earlier report at `reports/Startup regulatory grey areas 2026.md`. These notes focus on business models and economics.

## 1. FDA Jan 2026 wellness / CDS guidance: wellness wearables (BP, glucose, SpO2) and single-recommendation CDS / AI

### Takeaway
The guidance relaxes the rules by limiting what products may claim. It does not create a new product category. The proven money model is a consumer hardware-plus-subscription product with wellness-only claims (WHOOP is the template). On the clinician side it is CDS that is free to doctors and funded by ads (OpenEvidence). New entrants need validation data and tight claim discipline. A non-invasive glucose estimate qualifies only if it is contraindicated for people with diabetes or prediabetes, which shrinks the market for glucose features.

### Cited Findings
- FDA updated its General Wellness policy on Jan 6, 2026. Non-invasive wearables that estimate BP, glucose or SpO2 can be wellness products if they do not diagnose or treat, do not prompt clinical action, and do not display values that mimic clinical ones unless validated — [Womble Bond Dickinson](https://www.womblebonddickinson.com/us/insights/blogs/fdas-2026-general-wellness-policy-and-what-it-means-manufacturers-wearable-devices); [Covington, Jan 2026](https://www.cov.com/news-and-insights/insights/2026/01/fda-issues-revised-guidance-on-general-wellness-products); [King & Spalding](https://www.kslaw.com/insights/articles/fda-updates-general-wellness-and-clinical-decision-support-guidance-documents)
- Limits on what qualifies (2026):
  - A glucose wearable that uses minimally invasive microneedles is **not** low risk, even with wellness-only claims.
  - A non-invasive glucose estimate for nutrition qualifies only if it is explicitly contraindicated for diabetics and pre-diabetics.
  - Source: [Womble Bond Dickinson / King & Spalding summaries above](https://www.kslaw.com/insights/articles/fda-updates-general-wellness-and-clinical-decision-support-guidance-documents)
- WHOOP timeline:
  - FDA issued a warning letter on the "Blood Pressure Insights" feature in July 2025.
  - The letter was still unresolved as of May 22, 2026 ([Boston Globe](https://www.bostonglobe.com/2026/05/22/business/whoop-fda-blood-pressure-feature/)).
  - FDA closed it on Jun 17, 2026, after WHOOP made modifications and the new guidance took effect. A law firm calls this a "wellness playbook" ([ArentFox Schiff](https://www.afslaw.com/perspectives/alerts/not-fdas-whoop-ing-boy-how-warning-letter-became-wellness-playbook); [Design News](https://www.designnews.com/medical/fda-backs-down-on-whoop-blood-pressure-monitoring-dispute)).
- An industry analysis questions whether the BP rules "really changed," pointing to the requirement that clinical-looking values be validated — [Hardian Health, 2026](https://www.hardianhealth.com/insights/fda-wearables-guidelines-update-2026)
- OpenEvidence (clinical AI; secondary estimates):
  - Revenue: about $150M annualized in 2025, up from $7.9M in 2024, with a reported 90% gross margin ([Sacra](https://sacra.com/research/openevidence)).
  - Model: free to physicians and funded by ads ([webpronews, Jan 2026](https://www.webpronews.com/openevidences-12-billion-leap-ai-heals-the-funding-gap-for-doctors/)).
  - Funding: $250M Series D at $12B in Jan 2026 ([parsers.vc](https://parsers.vc/news/260123-openevidence-secures-250m--valuation-soars/)).
  - Later reports, which conflict with each other, describe a $15B round in Sep 2026 and a run-rate of about $300M by Q3 2026 ([aiweekly](https://aiweekly.co/alerts/openevidence-raises-250m-at-15b-25-above-januarys-12b-mark-and-weighing-sale); [healthcare.digital](https://www.healthcare.digital/single-post/nelson-advisors-openevidence-secures-250-million-alternative-financing-round-led-by-andreessen-hor)).
  - Volume: about 20M clinical consultations a month in Jan 2026 (same sources).
- Revised CDS guidance (Jan 2026) extends enforcement discretion to tools that give a single recommendation, including some AI — [Covington](https://www.cov.com/en/news-and-insights/insights/2026/01/5-key-takeaways-from-fdas-revised-clinical-decision-support-cds-software-guidance)

### Inferences
- **Model A, consumer wearable plus subscription.** Who pays: the consumer, through a hardware charge and/or a monthly subscription.
  - Startup cost: high for new hardware (sensor validation and manufacturing; likely $5–20M+ before launch). It is low if the product is a software layer that adds "wellness BP/HRV estimates" to existing devices (Apple Watch, Oura, Garmin APIs).
  - The cheapest entry is software-only: wellness analytics on third-party sensors, or B2B white-label algorithms sold to device makers.
- **Model B, CDS / AI for clinicians.** Who pays: advertisers (pharma), health-system licenses, or EHR marketplaces.
  - OpenEvidence shows that a free-to-clinician, ad-funded model reaches very large scale, but the category is now crowded at the top.
  - New entrants are more likely to win in narrow specialties (single-recommendation tools for dermatology, dosing, prior-auth support) sold per seat to clinics.
- **Window.** It stays open until FDA withdraws the discretion, which needs no notice and comment, or until adverse-event enforcement begins. Expect at least 2–3 years under the current administration.
- **Risks.**
  - Claim creep (any "hypertension" language), validation demands, state consumer-protection or UDAP suits, and app store and Amazon policy.
  - The glucose contraindication sharply limits the obvious diabetes market.

### Gaps
- No named wearable launched BP or glucose wellness estimates after January 2026 could be confirmed. Search results found none, so the launch pipeline is unverified.
- No public gross margins for WHOOP or Oura, and no subscription pricing confirmed in this research.
- No data on CDS startups that launched specifically because of the January 2026 CDS revision.

## 2. AI health coaching vs. AI therapy bans: compliant models and revenue

### Takeaway
As of Jul 20, 2026, four states ban AI-delivered therapy: Illinois, Nevada, Rhode Island and Maine. Others impose disclosure or safety rules: Utah, New York, California and Nebraska. Illinois also bars licensed clinicians from letting AI interact therapeutically with clients or detect emotions, so "clinician-in-the-loop" there means AI for admin and documentation only. The viable models are:
- (a) consumer "coaching/wellness" subscriptions that geoblock or carve out the ban states;
- (b) clinician-facing tools (notes, measurement, between-session homework approved by the clinician) sold per clinician seat;
- (c) employer and EAP coaching contracts.

### Cited Findings
- Four ban states as of Jul 20, 2026 — [Psychology.com map](https://psychology.com/ai-therapy/state-bans):
  - Illinois, effective Aug 2025.
  - Nevada, AB 406, effective Jul 1, 2025.
  - Rhode Island, June 2026.
  - Maine, effective Jul 29, 2026.
  - Disclosure and safety regimes apply in Utah, NY, CA and NE (same source).
- Becker's counts five states restricting AI therapy chatbots in 2026, citing the Transparency Coalition. Maine also bars licensed providers from using AI to make independent therapeutic decisions or treatment plans — [Becker's Behavioral Health](https://www.beckersbehavioralhealth.com/ai-2/5-states-restrict-ai-therapy-chatbots-in-2026/). (The trackers' counts conflict.)
- Illinois WOPR Act (Aug 1, 2025):
  - Bans therapy offered or advertised through AI unless a licensed professional performs it.
  - Licensed professionals may not let AI make independent therapeutic decisions, interact directly with clients in therapeutic communication, generate treatment plans without review, or detect emotions or mental states.
  - Source: [Holland & Knight](https://www.hklaw.com/en/insights/publications/2025/08/new-illinois-law-restricts-use-of-ai-in-mental-health-therapy)
- Example new entrant, The Path (consumer AI mental-health subscription co-founded by Tony Robbins and former Calm staff):
  - Raised a $14.3M seed in May 2026 led by Prime Movers Lab, using CBT/ACT/DBT frameworks ([HLTH, May 22, 2026](https://hlth.com/insights/news/ai-mental-health-startup-the-path-raises-14-3m); [MobiHealthNews](https://cloudgate.mobihealthnews.com/news/tony-robbins-ai-mental-health-startup-path-raises-143m)).
  - Reported 50,000+ members and 2.5M sessions ([Simplify listing — single aggregator, low confidence](https://simplify.jobs/c/The-Path)).

### Inferences
- **Compliant model 1: consumer AI "wellness coaching" subscription** (roughly $10–30/month, typical of consumer wellness apps; no specific source).
  - Do not use "therapy" or "therapist" marketing.
  - Geofence IL, NV, RI and ME, or ship a non-therapeutic product variant there.
  - Build crisis escalation and disclosures to satisfy UT, NY and CA.
  - Startup cost: low ($0.5–2M seed) using foundation-model APIs. The main costs are customer acquisition, safety and red-teaming, and legal review.
- **Compliant model 2: clinician-side tools.**
  - Ambient notes, measurement-based care, and between-session exercises that the clinician approves.
  - Priced per clinician seat (SaaS) or bundled into group practices.
  - This works even in Illinois, provided the AI does not interact therapeutically or detect emotions.
- **Compliant model 3: hybrid "AI plus licensed human" care.**
  - Billed to insurance or employers, with the licensed clinician as the provider of record.
  - Revenue per member is higher, but operations cost more: multistate licensure and an MSO/PC structure.
- **Window.** Shrinking. More states copy the Illinois approach each session, and the term "therapy" will keep being defined broadly.
- **Risks.** Illinois fines of up to $10k per violation, Nevada penalties of up to $15k (from the earlier report), the California SB 243 private right of action for companion bots, and FTC and state UDAP enforcement.

### Gaps
- No unit economics (CAC, retention, ARPU) were found for AI coaching apps.
- No 2026 enterprise or payer-funded, clinician-supervised AI coaching raises were found beyond The Path.
- Tennessee and Vermont status could not be reconciled across trackers.

## 3. Cash-pay healthcare: TrumpRx / DTC pharma, DPC with HSAs, cash telehealth after the GLP-1 compounding crackdown

### Takeaway
Cash pay is growing. Value is shifting from compounding margin to "platform plus branded cash drugs." TrumpRx is a referral hub. It sends demand to manufacturer DTC programs and to GoodRx, Cost Plus and Amazon, so a startup's role is care delivery and wraparound services (labs, coaching, adherence) around cheap branded drugs. Hims is the scale proof: revenue up 38% y/y, ARPU $92 a month, and gross margin compressing. Direct primary care gets a real tax tailwind: from Jan 1, 2026, HSA-compatible DPC is allowed if fees stay at or below $150 a month for an individual or $300 for a family. Employers already fund about 60% of DPC memberships at about $55–65 per member per month.

### Cited Findings
- **TrumpRx:**
  - Launch (Feb 5, 2026): drugs from AstraZeneca, Lilly, Merck/EMD Serono, Novo and Pfizer. Prices included Wegovy pill $149, some Wegovy pen doses $199 and Zepbound from $299.
  - Model: TrumpRx refers patients and does not dispense; partner platforms execute the price. GoodRx is the main integrator, and Cost Plus Drugs is also a partner ([pharmaphorum](https://pharmaphorum.com/news/white-houses-trumprx-platform-has-arrived); [Truveris](https://truveris.com/trumprx-launch-what-employers-and-benefits-consultants-should-know/)).
  - Expansion (May 2026): about 600 generics through Cost Plus, Amazon Pharmacy and GoodRx, and more than 10M site visits ([Drug Topics, May 19, 2026](https://www.drugtopics.com/view/trumprx-adds-nearly-600-generic-drugs-to-website)).
  - Limitation: DTC purchases usually don't count toward deductibles (same).
- **Hims & Hers Q2 2026** (reported Aug 2026; [10-Q](https://www.sec.gov/Archives/edgar/data/0001773751/000177375126000163/hims-20260630.htm); [8-K](https://www.sec.gov/Archives/edgar/data/0001773751/000177375126000161/hims-20260630x8xkearningsr.htm)):
  - About 2.9M subscribers, up 19% y/y, helped by the Eucalyptus acquisition.
  - Revenue about $753M, up 38%.
  - Monthly revenue per average subscriber $92, up from $76.
  - FY26 revenue guidance $3.1–3.3B.
  - Gross margin about 64% vs. 82% in 2023 (secondary analysis — [Kavout](https://www.kavout.com/market-lens/hims-hers-s-glp-1-revenue-surge-erodes-core-profitability)).
  - Earlier, Hims agreed to stop promoting compounded GLP-1s and to sell branded drugs at cash prices after Novo dismissed its suit ([Hims Q1 10-Q](https://www.sec.gov/Archives/edgar/data/0001773751/000177375126000076/hims-20260331.htm)).
- **DPC and HSA rule:**
  - From Jan 1, 2026, a DPC arrangement does not disqualify HSA contributions if fees are at most $150 a month (individual) or $300 (family), indexed for inflation. The cap is aggregate across arrangements. IRS Notice 2026-5 is the implementing guidance.
  - Excluded: lab services not typical of ambulatory primary care. Concierge arrangements with extra compensation do not qualify.
  - DPC fees can be paid from the HSA.
  - Sources: [HUB International](https://www.hubinternational.com/hub-resources/employee-benefits-compliance-bulletins/2025/08/direct-primary-care-rules-for-hsa-plans-under-the-obbba); [GoodRx](https://goodrx.com/insurance/fsa-hsa/hsa-one-big-beautiful-bill); [USI](https://info.usi.com/rs/121-VCO-807/images/Guidance_on_HSA_Provisions_in_OBBBA_Dec_11_2025.pdf?version=0)
- **DPC economics** (2026 State of DPC survey: 465 physicians, data collected late 2024, published Jul 2026, about 3,600 US DPC practices):
  - Average membership fee: $98.60 a month.
  - By panel size: practices under 200 patients average about $106; practices over 500 average about $78.
  - Mature panels are 400–700 patients, and 68.4% of practices say their panels are not yet full.
  - Sources: [Hint blog](https://blog.hint.com/state-of-dpc-2026-key-takeaways-from-the-dpc-alliances-physician-survey); [Medical Economics, Jul 29, 2026](https://www.medicaleconomics.com/view/five-surprising-findings-about-the-state-of-direct-primary-care)
- AAFP fee ranges: adults $50–150 a month; youth $20–49; families $100+ — [Healio, Sep 1, 2026](https://www.healio.com/news/primary-care/20260901/direct-primary-care-gains-momentum-as-experts-weigh-benefits-and-tradeoffs)
- Employers fund about 60% of active DPC memberships, and employer rates have held at $55–65 for five years (Hint report, secondhand via [DPC News](https://dpcnews.com/direct-primary-care-statistics/direct-primary-care-statistic-of-the-week-2/)).
- DPC startup cost ranges from about $5,000 (low overhead) to $100,000+ (traditional office), per a 2020 FPM figure cited by [AAFP](https://www.aafp.org/pubs/fpm/blogs/inpractice/entry/dpc-faqs.html). That is an older figure. Break-even is about 12–24 months ([ZenBusiness — low authority](https://www.zenbusiness.com/start-a-business/healthcare/direct-primary-care/)).

### Inferences
- **DPC unit economics** (rough, from the survey figures): a solo physician with 500 patients at about $80 a month earns about $480k a year in gross revenue.
- **Best startup plays:**
  - (a) DPC enablement: billing and membership software (Hint, Elation), HSA-compliance "DPC-in-a-box," and employer DPC networks. Paid per member per month by practices or employers.
  - (b) Designs priced at or under $150 that bundle HSA-compatible DPC with Bronze or catastrophic plans for the self-employed.
  - (c) Cash GLP-1 and metabolic care built around TrumpRx/DTC branded pricing, monetized through a clinical membership ($50–150 a month is typical of the category) rather than drug margin.
- **Risks for cash GLP-1:**
  - Branded price cuts compress platform value.
  - Lilly and Novo DTC channels compete directly.
  - Telehealth platforms face the FDA/DOJ marketing crackdown (warning-letter waves in March and June 2026, per the earlier report).
  - Prescribing tied to controlled substances (e.g., phentermine) faces the Dec 31 DEA cliff.
- **Window.**
  - The DPC/HSA change is statutory and durable, a multi-year window.
  - The TrumpRx-linked advantage depends on administration policy.

### Gaps
- No public list of telehealth partners integrated with TrumpRx.
- No 2026 count of new DPC practices or employer adoption after OBBBA.
- No Hims GLP-1 subscriber split.
- No figures for smaller cash telehealth entrants (e.g., Ro, Found, Noom) beyond Hims.

## 4. Psychedelics: April 2026 EO, FDA vouchers, Right to Try, state programs

### Takeaway
Federal momentum is real: the Apr 18, 2026 EO, priority vouchers on Apr 24 and a Right to Try pathway now being built. But the near-term money is in state programs and services, not in drugs. Oregon shows that retail session centers are a hard business: about a third of centers had closed by January 2026, license fees are $10k a year with a proposal to double them, and the well-known InnerTrek pivoted to training. Better models:
- training and certification across the growing set of states (CO, NM; Oregon has more than 10 programs);
- compliance and EHR/outcomes software (an inference);
- clinic infrastructure ready for FDA approval of psilocybin and for Right to Try ibogaine;
- research and site services for state-funded trials (Texas $50M).

### Cited Findings
- **EO "Accelerating Medical Treatments for Serious Mental Illness"** (signed Apr 18, 2026; [Foley](https://www.foley.com/insights/publications/2026/04/psychedelics-and-the-executive-order-from-schedule-i-to-treatment-priority/); [Harris Sliwoski](https://harris-sliwoski.com/psychlawblog/trumps-executive-order-on-psychedelics/)):
  - Directs FDA and DEA to create a Right to Try pathway, including for ibogaine compounds, with Schedule I handling authorizations.
  - Directs priority vouchers for psychedelic candidates that hold Breakthrough designation.
- Vouchers went on Apr 24 to Compass (COMP360), Usona (psilocybin for MDD) and Transcend (methylone for PTSD). FDA also cleared a Phase 1 trial of noribogaine (same sources).
- Federal funding figures conflict: "at least $50M" through ARPA-H for state programs ([Foley](https://www.foley.com/insights/publications/2026/04/psychedelics-and-the-executive-order-from-schedule-i-to-treatment-priority/)) vs. "more than $139M" ([Baker Donelson](https://www.bakerdonelson.com/executive-order-on-psychedelic-medicine-unprecedented-federal-funding-and-policy-alignment-for-physicians-practices-and-research-organizations)). This is unresolved.
- Baker Donelson calls the early-mover window "significant but time-limited" and cites Lilly's acquisition of AtaiBeckley (same source).
- **Oregon:**
  - About one third of service centers had closed by January 2026; the early-January state tally was 23 licensed, 6 surrendered and 6 expired ([OPB, Jan 22, 2026](https://opb.org/article/2026/01/22/think-out-loud-oregon-licensed-psilocybin)).
  - Center license costs $10k a year. In July 2026, OHA proposed doubling fees and ending nonprofit and low-income discounts ([OPB, Jul 16, 2026](https://www.opb.org/article/2026/07/16/licensing-fees-could-double-for-oregon-psilocybin-service-centers-and-facilitators/)).
  - InnerTrek closed its Portland service center in June 2026 and shifted to training. It charged about $850 for group sessions and about $1,500 for individual sessions ([Willamette Week, Jun 30, 2026](https://www.wweek.com/news/health/2026/06/30/in-change-of-tack-major-portland-psilocybin-service-center-closes/)).
  - Oregon has 10+ approved training programs, and some students do their practicum in Colorado (same/[mindmedicinelaw](https://mindmedicinelaw.com/briefing/oregon-psilocybin-center-closure-implications-for-policy-and-market-20260630-17975)).
- **Colorado healing-center prices** (marketing sources, undated): typically about $1,000–3,000 or more per session.
  - Boulder examples: about $2,800 at Happy Rebel, $1,500–3,000 at Chariot, $3,400 at Psychedelic Growth.
  - No insurance coverage.
  - Sources: [HealingMaps](https://healingmaps.com/boulder-becomes-hub-for-colorados-first-three-psilocybin-healing-centers/); [mindmedicinelaw](https://mindmedicinelaw.com/law/colorado-proposition-122)
- **New Mexico** (Medical Psilocybin Act, SB 219):
  - The state plans to launch by the end of December 2026, a year ahead of the Dec 31, 2027 statutory deadline.
  - Training standards are being drafted for clinicians, Indigenous healers, doulas and others.
  - The FY budget includes a $630k Treatment Equity Fund.
  - Sources: [Filter](https://filtermag.org/new-mexico-accelerate-psilocybin-access/); [MAPS Q2 2026 wrap](https://maps.org/2026/07/08/2026-second-quarter-policy-advocacy-wrap-up/)
- **Texas ibogaine:** SB 2308 set up a consortium with matching funds. In March 2026, Texas launched its own research program using the $50M appropriation after failing to find a drug-developer partner — [News From The States](https://www.newsfromthestates.com/article/texas-will-launch-its-own-clinical-trials-ibogaine-psychedelic-after-failing-find-drug)

### Inferences
- **Training and certification** (tuition paid by individuals): a low-capex model with multistate demand (NM workforce build-out in 2026–27, CO practicums). It is the clearest current cash generator, and Oregon operators are moving into it.
- **Clinic or healing-center model** (consumer cash at about $1–3.5k per session):
  - Fixed costs and licensing are high, and volume is low.
  - Unit economics in Oregon look poor.
  - Colorado is better but unproven. New Mexico is publicly subsidized and medical.
- **Software:** scheduling and compliance reporting for state regulators, facilitator credentialing, and outcomes data. Sold as SaaS to centers, or to states and research consortia.
- **Pre-positioning:** sites ready for FDA approval or REMS, i.e. ketamine/Spravato-style clinics that can add psilocybin if Compass or Usona win approval.
- **Window.** State programs: now. FDA-approved psilocybin: probably 2027+ (Compass has a voucher). Right to Try ibogaine: depends on FDA/DEA implementation, which is not yet built.
- **Risks.** Schedule I status, DEA registration, and state fee hikes such as Oregon's.

### Gaps
- No verified FDA approval date or PDUFA date for COMP360.
- No details on whether the FDA/DEA Right to Try implementation is operational as of Oct 2026.
- No revenue data for training programs or software vendors (e.g., Osmind).
- No Colorado center count or volume data for 2026.

## 5. Peptides / longevity clinics after April 2026 Category 2 changes; DEA telehealth Dec 31, 2026 cliff

### Takeaway
Removing 12 peptides from Category 2 (Apr 15, 2026) did not clearly make them compoundable. Lawyers say BPC-157 is in limbo until it is added to Category 1 or the 503A bulks list (PCAC review Jul 23, 2026), while marketing sites say pharmacies can fill it. Durable longevity revenue sits in lab-testing memberships (Function Health: $365 a year, 500k+ members). Peptide prescribing is a high-margin add-on with legal tail risk. For the DEA cliff, the final special-registration rule has been at OIRA since Aug 25, 2026 with its text unpublished. The concrete service opportunities are identity verification, PDMP checks, credentialing and per-state registration management, and DEA data reporting.

### Cited Findings
- **Peptides:**
  - HHS/FDA removed 12 peptides, including BPC-157, from Category 2 (Federal Register notice and 503A page dated Apr 15, 2026; Docket FDA-2025-N-6895) ([503Pharma](https://503pharma-newsletter.beehiiv.com/p/breaking-fda-pulls-12-peptides-from-category-2-list)).
  - PCAC review of BPC-157 was set for Jul 23, 2026 (same).
  - DJ Holt Law: the removal happened because nominators withdrew. BPC-157 now meets no 503A criterion and is in "regulatory limbo" ([DJ Holt Law](https://djholtlaw.com/regulatory-alert-fdas-april-2026-update-on-bpc-157-and-ghk-cu/)).
  - This conflicts with consumer and marketing pages that say compounding pharmacies can fill prescriptions ([HealingMaps](https://healingmaps.com/bpc-157-wolverine-peptide-injury-recovery/); [Rite Aid page](https://riteaid.com/peptides/bpc-157)).
- **Function Health:**
  - Cut its price to $365 a year in late 2025 (from $499) when it raised a $298M Series B at $2.5B ([Athletech News](https://athletechnews.com/function-health-raises-298-million-at-2-5-billion-valuation/)).
  - Reached 500k+ members by July 2026 and raised $450M of growth financing led by General Catalyst ([Athletech News](https://athletechnews.com/function-450-million-growth-financing-general-catalyst/)).
  - Revenue estimate: about $110–164M a year (third-party estimate); add-ons include a $499 full-body MRI ([newmarketpitch](https://newmarketpitch.com/blogs/news/digital-health-function-health-overvalued); [Sacra](https://sacra.com/research/function-health-at-100m-year/)).
- Superpower ("digital clinic," longevity) raised a $30M Series A in April 2025 led by Forerunner — [Sacra](https://sacra.com/c/superpower/)
- **DEA cliff:**
  - The final special-registration rule went to OIRA on Aug 25, 2026, and its text is not public. It may be finalized before the Dec 31, 2026 expiry ([McDermott](https://www.mcdermottlaw.com/insights/dea-telemedicine-flexibilities-for-controlled-substances-2026/)).
  - The January 2025 proposed rule had three special registrations. Its requirements ([McDermott](https://www.mcdermottlaw.com/insights/dea-telemedicine-flexibilities-for-controlled-substances-2026/); [Lashly & Baer](https://www.lashlybaer.com/dea-provides-fourth-extension-of-rules-allowing-telemedicine-prescribing-of-controlled-substances/)):
    - PDMP checks and audio-video visits;
    - Schedule II limits;
    - DEA data reporting;
    - identity verification;
    - credentialing and record retention;
    - a "legitimate need" showing for platforms;
    - a separate State Telemedicine Registration for each patient state.

### Inferences
- **Longevity models:**
  - (a) Lab-membership subscription: consumer pays about $199–499 a year, lab cost-of-goods are high, revenue comes from add-ons (imaging, Rx).
  - (b) Cash clinic: peptides, TRT, GLP-1 plus coaching at roughly $150–500 a month (category pricing, not sourced).
  - Peptides are the riskiest add-on. Pharmacy-board and FDA action against 503A pharmacies would cut supply overnight, and TRT and other Schedule III drugs are exposed to the DEA cliff.
- **DEA compliance services:**
  - Who pays: telehealth platforms and multistate practices.
  - Offer: compliance SaaS or managed service (registration filing and tracking in each state, PDMP integration, ID proofing, Schedule II workflow, DEA reporting) and in-person referral networks for the hybrid hedge.
  - Startup cost: low to moderate (software plus regulatory staff).
  - Window: acute from now through Q1 2027. It becomes a recurring compliance product if the rule is finalized. If DEA issues a fifth extension, urgency fades, which is the key risk.

### Gaps
- PCAC Jul 23, 2026 outcome on BPC-157 not found; check before relying on it.
- No vendor directory for DEA special-registration compliance, and no pricing.
- No peptide clinic revenue or margin data.

## 6. Hemp after the Dec 11, 2026 federal ban

### Takeaway
The intoxicating hemp market is closing. The finished-product cap is 0.4 mg total THC per container, THCA counts toward it, and synthetic cannabinoids are excluded. Money plays are:
- **(1) liquidating inventory before retailers stop buying;**
- **(2) state-licensed channels**, such as low-THC hemp-intoxicant licenses or moving brands into licensed cannabis in MN, TN and similar states;
- **(3) non-intoxicating or industrial products** (fiber, grain, reformulated minor cannabinoids without THC);
- **(4) services:** compliance testing, reformulation, brand licensing to MSOs, and the beverage brands moving into alcohol distribution.

### Cited Findings
- New definition: a 0.4 mg total THC cap per container for finished hemp-derived products, with THCA included. Lab-made or non-naturally-occurring cannabinoids are excluded. The US Hemp Roundtable says most non-intoxicating CBD products also exceed 0.4 mg per container — [KCUR, Sep 17, 2026](https://www.kcur.org/environment-agriculture/2026-09-17/hemp-federal-ban-thc-growers)
- The effective date was pushed to Dec 11, 2026 (except synthetics) — [Forbes, Sep 3, 2026](https://www.forbes.com/sites/ajherrington/2026/09/03/trump-signs-bill-delaying-hemp-thc-ban-until-december/); [Cannabis Law Blog](https://www.cannabis-law-blog.com/federal-intoxicating-hemp-ban-changes-pushed-back-until-december-11-2026/)
- Advisories recommend:
  - "tapered liquidation," since retailers are unlikely to buy noncompliant inventory late in 2026;
  - auditing SKUs that rely on Delta-8 or THCA;
  - reformulating around minor cannabinoids, moving to non-consumable industrial markets, or applying for state low-THC hemp-intoxicant licenses.
  - MN and TN are folding hemp into their cannabis frameworks.
  - Sources: [HBK CPA](https://hbkcpa.com/insights/federal-hemp-ban-business-guide/); [Seedless](https://seedless.media/hemp-industry-survival-strategy-2026-lessons/); [Sheppard Mullin](https://www.sheppard.com/insights/blogs/cannabis-in-2026-part-ii-hemp-tightening-in-2026-the-compliance-cliff-cbd-carve-out-signals-and-business-risk)
- Ohio: the governor vetoed a beverage exception in March 2026. An injunction protects only products from 10 plaintiff companies, and the state is seeking a stay — [MJBizDaily](https://mjbizdaily.com/ohio-will-allow-hemp-thc-drinks-amid-federal-ban-with-conditions/); [Cannabis Legalization News](https://cannabislegalizationnews.com/ohio-thc-drinks-injunction/)
- Washington precedent: licensed hemp growers fell from 220 to 42 after intoxicating hemp moved into the regulated cannabis market (via [Barchart/AP](https://www.barchart.com/story/news/36351501/here-s-what-to-know-about-the-federal-ban-threatening-the-market-for-thc-infused-drinks-and-snacks)).
- Craft brewers who added THC seltzers are also exposed — [Ollie](https://getollie.com/blog/the-federal-hemp-ban-is-a-craft-brewer-problem-too)

### Inferences
- **Buyer-side plays (low startup cost, short window to about Q1 2027):**
  - distressed-asset purchases: extraction equipment, brands, retail shelf contracts;
  - inventory clearing and destruction-compliance services;
  - bringing hemp beverage brands into state-licensed cannabis markets through licensing deals with MSOs.
- **Non-intoxicating pivot:** functional beverages (adaptogens, kava, mushrooms that are not psilocybin). Margins are lower but national distribution remains.
- **Durability:** state-licensed cannabis is durable but needs capital and licenses. Washington shows consolidation follows.
- **Upside optionality:** Congress could still attach a regulatory framework to the FY2027 appropriations. As of Sep 30, no regulate-not-ban bill had had a hearing (from the earlier report).

### Gaps
- No reporting confirms companies moving to Minnesota licenses because of the ban.
- No inventory-liquidation pricing or volume data.
- No data on the size of the hemp-beverage market that is migrating.
