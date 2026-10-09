# Compliance Tooling and Fintech/Tokenization Money Plays in 2025–2026 Regulatory Openings (as of Oct 9, 2026)

Scope note: policy facts are in `reports/Startup regulatory grey areas 2026.md`. These notes cover business models, buyers, pricing, competition and windows. Research covered about 17 searches and fetches. Many search hits were aggregators or vendor blogs; reliability flags appear inline. TechCrunch was blocked by the egress proxy, so TechCrunch items are cited from search snippets only and could not be read in full.

## 1. AI compliance tooling (CA SB 243 / SB 53, NY RAISE, Colorado, EU AI Act Art. 50 and high-risk, C2PA)

### Takeaway
Money is flowing into "agentic GRC" and AI-agent security/governance, with $20–40M Series A rounds in May–Sept 2026. Incumbent AI-governance platforms (Credo AI, Holistic AI) sell only on custom enterprise quotes, with no public list prices. The clearest dated forcing function is the EU Art. 50 machine-readable marking deadline (Dec 2, 2026 for systems already on the market). However, frontier model providers are already doing their own marking, which squeezes standalone watermark vendors. The startup opening is mid-market and downstream deployers, plus narrow statute-specific tooling such as SB 243 crisis-protocol reporting. Neither is well served by named vendors.

### Cited Findings
- **Comp AI** (Sept 2026) raised a **$34M Series A** led by Roo Capital and Grand Ventures. It is agentic compliance software that reads company systems and docs to draft policies and risk registers. It is moving into continuous post-audit monitoring. — [TechCrunch, Sept 17, 2026 (snippet only; fetch blocked)](https://techcrunch.com/2026/09/17/comp-ai-sets-eyes-on-a-continiously-agentic-future-for-security-and-complaince/); [MSSP Alert](https://www.msspalert.com/brief/comp-ai-raises-34-million-to-advance-ai-powered-compliance-software)
- **Geordie AI** (May 28, 2026) raised a **$30M Series A** led by Balderton for security and governance of AI agents, at about **$180M post-money**. — [Fortune, May 28, 2026](https://fortune.com/2026/05/28/geordie-security-governance-ai-agents/)
- Other 2026 rounds come from an aggregator and are unverified against primary sources:
  - Spektr: $20M Series A, June 2026, AI agents automating compliance analyst work.
  - Bayshore: $8M seed, June 2026, led by Earlybird; turns regulations into machine-readable rules.
  - Hush Security: $30M Series A, July 28, 2026.
  - Gray Swan: $40M Series A, May 28, 2026.
  - JetStream Security: $34M seed, Q1 2026.
  — [NewMarketPitch AI governance deals](https://newmarketpitch.com/blogs/news/ai-governance-funding-deals); [NewMarketPitch Sept 2026](https://newmarketpitch.com/blogs/news/ai-governance-funding-news)
- Adjacent: TeddyHoldings.AI raised a **$60M seed** (Oct 7, 2026) and reports **>$25M revenue**. It is a legal-services compliance and client-service platform, so it is only loosely AI governance. — [FinSMEs, Oct 2026](https://finsmes.com/2026/10/teddyholdings-ai-raises-60m-in-seed-funding.html)
- **Pricing:** Credo AI sells a single custom-quoted Enterprise plan billed by **number of governed AI use cases**, with per-use-case overage. It covers EU AI Act, NIST AI RMF and ISO 42001. Its AWS Marketplace listing shows a placeholder "$1" private offer. Holistic AI shows "contact sales". A comparison of Credo, Holistic and Fairly AI says all three are quote-only with no self-serve tier. — [ComparEdge (third-party)](https://comparedge.com/tools/credo-ai/pricing); [AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-x67krdatcdday); [Decryption Digest](https://www.decryptiondigest.com/blog/eu-ai-act-compliance-platforms-credo-ai-vs-holistic-ai-vs-fairly-ai)
- **EU Art. 50:**
  - Enforceable from Aug 2, 2026. The May 2026 AI Omnibus provisional deal gave gen-AI systems already on the market until **Dec 2, 2026** to add machine-readable marking.
  - The Code of Practice asks for **at least two machine-readable techniques**, for example signed metadata plus an imperceptible watermark.
  - C2PA is the reference standard in the Code but is not named in the Act.
  — [InfoQ, Aug 2026](https://www.infoq.com/news/2026/08/eu-ai-content-watermark/); [Paul, Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content)
- **Frontier providers handle their own marking.** Major providers adopted watermarking to comply. One source says OpenAI embeds C2PA metadata alongside SynthID-style pixel watermarks; this is lower-quality sourcing. Open-source options exist, including c2pa-rs and Meta AudioSeal/VideoSeal. — [InfoQ, Aug 2026](https://www.infoq.com/news/2026/08/eu-ai-content-watermark/); [Lyceum (lower quality)](https://lyceum.technology/magazine/article-50-ai-act-marking-outputs-with-c2pa/)
- Sources conflict on the Code of Practice finalization date: June 10 vs July 20, 2026. — [aggregated in search; see Paul, Weiss](https://www.paulweiss.com/insights/client-memos/eu-finalises-transparency-rules-for-ai-generated-content)
- **SB 243** (effective Jan 1, 2026) covers startups and enterprises running companion chatbots used by Californians. Using a vendor's model does not exempt the deployer. Crisis protocols and crisis-notification statistics must be reported to the state. — [Shelly Palmer, Oct 2025](https://shellypalmer.com/2025/10/california-regulates-ai-companion-chatbots/); [Nat'l Law Review](https://natlawreview.com/article/ai-regulatory-update-californias-sb-243-mandates-companion-ai-safety-and)

### Inferences
- **Model options:**
  - **(a) Agentic GRC SaaS.** Annual subscription, priced per framework or per AI use case, mirroring Credo's per-use-case metering. Sold to the CISO, GC or compliance lead at mid-market AI deployers.
  - **(b) Statute-specific "compliance kits".** SB 243 self-harm detection, referral, logging and annual reporting, or RAISE/SB 53 frontier-safety-framework documentation. Usage-based API pricing sold to companion-app and chatbot startups. No named vendor surfaced, so this looks white-space.
  - **(c) Provenance verification and detection** for platforms and publishers (the receiving side of C2PA), rather than marking. Marking is being commoditized by model providers and open source.
- **Startup cost is low**: software-only, roughly a seed round, with no licenses. The moats are distribution, audit-firm partnerships and a regulatory-mapping corpus.
- **Competition** includes horizontal GRC incumbents (Vanta, Drata, OneTrust) adding AI modules. This is not sourced here and is background knowledge. The funded Series A cohort above is also a competitor.
- **Window:** EU Dec 2, 2026 marking and Aug 2027–28 high-risk deadlines give a 12–24 month demand pulse. US state AI-law demand is exposed to federal preemption pressure (see prior report), so revenue tied to a single US statute is fragile.

### Gaps
- No published pricing for any AI-governance or watermarking vendor. ACV figures would need sales quotes or analyst data.
- No vendor found selling SB 243-, SB 53- or RAISE-specific tooling, and no data on budgets buyers allocate to it.
- Hush Security, Gray Swan, Spektr, Bayshore and JetStream rounds are aggregator-sourced only.
- Could not read TechCrunch due to the egress block.

## 2. Privacy compliance (20+ state laws, CCPA ADMT/risk assessments, COPPA, app-store age-verification laws)

### Takeaway
Regulatory demand is concrete and dated. CCPA risk assessments run from 2026, ADMT opt-out from Jan 1, 2027, and the first CPPA risk-assessment submissions are due Apr 1, 2028. App-store accountability laws are in force in Texas and Utah, with Louisiana from July 1, 2026, Alabama enacted, and California from Jan 1, 2027. However, the age-assurance vendor field (k-ID, Persona, Yoti, Incode, Veratad) is already funded and consolidating around reusable credentials. Google is building age signals into the OS and app store. New entrants should target developer-side integration and evidence/recordkeeping, not identity verification itself.

### Cited Findings
- **CCPA:**
  - The CCPA regulations on ADMT, risk assessments and cybersecurity audits took effect Jan 1, 2026, with phased compliance.
  - ADMT notice and opt-out duties begin Jan 1, 2027.
  - The first summary of 2026–27 risk assessments is due to the CPPA by **Apr 1, 2028**.
  - Regulators can demand full assessment reports within **30 days**.
  — [Mayer Brown, Jan 2026](https://www.mayerbrown.com/en/insights/publications/2026/01/updates-to-the-ccpa-regulations-what-businesses-need-to-know-now-about-automated-decision-making-cybersecurity-audits-and-risk-assessments); [CPPA announcement Sept 23, 2025](https://cppa.ca.gov/announcements/2025/20250923.html); [Thompson Coburn](https://www.thompsoncoburn.com/insights/californias-2026-ccpa-regulations-summary-and-preparation-guide/)
- Privacy vendors are already marketing CCPA ADMT and risk-assessment content, for example Privado's 2026 guide and Secure Privacy. — [Privado](https://www.privado.ai/ebooks/2026-ccpa-compliance-guide-for-new-requirements-risk-assessments-admt-cybersecurity-audits); [Secure Privacy](https://secureprivacy.ai/blog/ccpa-requirements-2026-complete-compliance-guide)
- **App-store laws:**
  - Texas SB 2420 is in effect after the Fifth Circuit stayed a preliminary injunction.
  - Google is rolling out age-verification signals and a Play Store flow for new Texas accounts.
  - Utah's law is listed as effective May 6, 2026 and Louisiana's July 1, 2026.
  - California's Digital Age Assurance Act (AB 1043) takes effect Jan 1, 2027.
  - Alabama HB 161 was signed Feb 17, 2026.
  — [MoFo](https://www.mofo.com/resources/insights/251111-texas-targets-app-stores-with-new-accountability-law); [Baker Data Counsel](https://www.bakerdatacounsel.com/blogs/an-app-developers-guide-to-app-store-age-assurance-laws/); [Wiley](https://www.wiley.law/alert-State-App-Store-Accountability-Acts-Introduce-New-Obligations-for-App-Developers); [Venable, Dec 2025](https://www.venable.com/insights/publications/2025/12/new-app-developer-compliance-requirements)
- The federal App Store Accountability Act (S.1586) was introduced May 1, 2025. No evidence was found that it advanced. — [Congress.gov](https://www.congress.gov/bill/119th-congress/senate-bill/1586/text)
- **Age-assurance incumbents:**
  - k-ID raised about $45M (2024) from a16z, Lightspeed and Konvoy.
  - In Jan 2026, Persona, Incode and Veratad joined k-ID's **OpenAge** reusable age-check network.
  - Persona reportedly raised a $200M Series D at a $2B valuation (Apr 2025); sources conflict.
  - Yoti has raised $130M+ (aggregator figure). It withdrew its Yoti ID app from Spanish app stores on Sept 10, 2026 after a €950K fine from the Spanish DPA (Mar 2026), which it is appealing.
  — [Biometric Update, Jan 2026](https://www.biometricupdate.com/202601/persona-incode-veratad-join-k-ids-openage-initiative-for-reusable-age-checks); [CB Insights k-ID](https://www.cbinsights.com/company/k-id); [Wikipedia Yoti](https://en.wikipedia.org/wiki/Yoti)
- No 2026 funding round was found for k-ID, Persona or Yoti in searches. — (search result, Oct 2026)

### Inferences
- **Age assurance is a scale game with entrenched, funded vendors.** Apple and Google are becoming the age-signal source under app-store laws, which shrinks per-app verification spend. A new entrant's angle is **developer-side compliance middleware**: consume the OS/app-store age signals, gate features, capture parental consent, log evidence for each state's rules, and handle the CA Jan 2027 regime. Price per MAU or a SaaS tier, sold to app developers' product and legal teams. Startup cost is low, but the window is narrow because platforms may bundle this.
- **CCPA ADMT and risk-assessment tooling** fits the existing privacy-ops category (OneTrust, TrustArc, Privado, Securiti; competitor list partly background knowledge). The Jan 2027 ADMT and Apr 2028 filing dates give a roughly 18-month sales window. Differentiation could come from automated discovery of ADMT use in code and data flows (Privado's approach) and from cross-mapping one assessment to the 20+ state DPIA requirements.
- Risk: Yoti's Spanish fine shows age-verification vendors carry privacy-regulator liability of their own.

### Gaps
- No pricing data found for age-assurance per-check fees or consent-management tiers.
- No 2026 funding rounds identified for privacy-compliance startups. The search returned only regulatory content.
- No data on COPPA-update-specific tooling.

## 3. Stablecoins / GENIUS: infrastructure, B2B and cross-border payments, licensing moats

### Takeaway
This is the hottest-funded area. Mastercard bought BVNK for up to $1.8B (closed about Aug 3, 2026). Stripe's Bridge got conditional OCC trust-charter approval (Feb 2026). Many $8M–$180M rounds closed in Jan–Aug 2026. Issuance-as-a-service is already crowded: Paxos, Brale, Agora, M0×Anchorage, Bridge. The plausible new-entrant plays are vertical or regional payment orchestration on top of licensed partners, plus compliance and attestation tooling for the GENIUS effective date (no later than Jan 18, 2027). Building a 50-state MTL footprint costs about $1.1–1.5M and 1–2+ years. That is a moat for incumbents, not a startup strategy.

### Cited Findings
- **Mastercard–BVNK.** The deal is $1.5B plus up to $300M contingent, for about $1.8B in total. It was announced Mar 17, 2026. It followed collapsed talks with Coinbase at about $2B (Nov 2025). Mastercard reports completion; a secondary source dates the close to Aug 3, 2026. — [CoinDesk, Mar 17, 2026](https://www.coindesk.com/business/2026/03/17/mastercard-agrees-to-purchase-bvnk-for-up-to-usd1-8-billion); [Mastercard IR](https://investor.mastercard.com/investor-news/investor-news-details/2026/Mastercard-completes-acquisition-of-BVNK-to-advance-global-stablecoin-capabilities/default.aspx); [Mastercard 10-Q](https://www.sec.gov/Archives/edgar/data/0001141391/000114139126000083/ma-20260630.htm)
- **Bridge (Stripe)** received conditional OCC national trust bank approval: Feb 12, 2026 per the OCC database, announced Feb 17. The charter would let it issue stablecoins, custody assets and manage reserves. Final approval has no set timeline. It follows the Dec 2025 conditional approvals for Circle, Ripple, BitGo, Fidelity Digital Assets and Paxos. — [CoinDesk, Feb 17, 2026](https://www.coindesk.com/business/2026/02/17/stripe-s-stablecoin-firm-bridge-wins-initial-approval-of-national-bank-trust-charter); [Payments Dive](https://www.paymentsdive.com/news/stripe-bridge-occ-conditional-approval-national-trust-bank-charter/812425/); [American Banker](https://www.americanbanker.com/payments/news/stripe-owned-bridge-acquires-trust-charter-for-stablecoins)
- An unverified wiki claim says Circle received final OCC approval on July 10, 2026. — [private.law wiki (single source)](https://wiki.private.law/en/bridge-stripe)
- **2026 rounds:**
  - **Augustus**: $180M (July 2026), a "stablecoin bank" clearing bank for AI-era settlement, with no own coin. — [CoinDesk, Jul 21, 2026](https://www.coindesk.com/business/2026/07/21/augustus-raises-usd180-million-to-build-a-clearing-bank-for-the-ai-and-stablecoin-era)
  - **OpenFX**: $94M (Mar 2026), stablecoin-powered cross-border FX, at about a $500M valuation per Reuters. — [CoinDesk, Mar 31, 2026](https://www.coindesk.com/business/2026/03/31/forex-startup-openfx-raises-usd94-million-to-expand-stablecoin-powered-cross-border-payments)
  - **Yellow Card**: $40M (Aug 2026), with >$120M total equity; backers include SC Ventures, Sony and Polychain. — [Fintech.global, Aug 4, 2026](https://fintech.global/2026/08/04/yellow-card-raises-40m-to-scale-stablecoin-rails-globally/)
  - **Velocity** (London): $38M Series A (July 2026), a treasury and settlement platform. Dragonfly and FirstMark led, with Coinbase, Capital One Ventures and Ripple participating. — [Fortune, Jul 14, 2026](https://fortune.com/2026/07/14/exclusive-payments-startup-velocity-38-million-businesses-stablecoin-growth/)
  - **Cyclops**: $20M Series A (July 2026). The lead is disputed: Nava Ventures vs SBI Holdings USA. — [Yahoo Finance](https://finance.yahoo.com/markets/crypto/articles/payments-focused-stablecoin-startup-cyclops-064841482.html)
  - **VelaFi** (LatAm): $20M Series B (Jan 2026). — [CoinDesk, Jan 12, 2026](https://www.coindesk.com/business/2026/01/12/velafi-raises-usd20-million-in-series-b-to-expand-stablecoin-payments-infrastructure)
  - **Checker**: $8M pre-seed and seed (May 2026), institutional stablecoin infrastructure, with Galaxy Ventures and Framework. — [The Block, May 19, 2026](https://www.theblock.co/news/deals/2026-05-19-stablecoin-infrastructure-startup-checker-funding-401906)
- **Issuance-as-a-service competitors** (sources are mostly vendor and aggregator blogs):
  - Paxos (PYUSD, USDG, USDP) runs bespoke, months-long branded issuance.
  - Brale is a white-label issuer operating under its own MTLs, on 20+ chains.
  - M0 is a programmable issuance protocol. On Apr 30, 2026 it announced a joint stack with Anchorage: M0 provides contracts and attestation pipelines, Anchorage provides reserves and compliance.
  - Agora offers AUSD-backed white-label coins claimed to launch "within one day".
  — [DeFi Prime map](https://defiprime.com/stablecoin-issuance-infrastructure-2026); [Bex, May 1, 2026](https://bex.co/blog/2026/05/01/anchorage-m0-modular-stablecoin-stack-genius-act); [Fintech Specs](https://fintechspecs.com/blog/best-stablecoin-issuance-platforms-fintechs/)
- **Licensing:**
  - About 48–49 states plus DC require an MTL.
  - A consultant estimate puts all-state applications at **$1.1–1.5M** plus bonds and audits.
  - Timelines run 3–4 months for fast states, 6–9 months typical, and over a year for CA, TX and NY. NY is 18–24+ months per one tool.
  - Transak example: it serves 46 states via partners, has 19 MTL applications pending, and targets all 50 states in 12–18 months.
  — [Faisal Khan (vendor)](https://faisalkhan.com/solutions/licensing/money-transmitter-license-mtl/money-transmitter-license-cost/); [Spark comparison](https://www.spark.money/tools/stablecoin-money-transmitter-license-comparison); [Yahoo/Transak](https://finance.yahoo.com/news/transak-expands-stablecoin-payments-6-180508273.html)
- K&L Gates (Oct 6, 2025) says payment stablecoins could replace or augment fintech models reliant on bank partnerships or MTLs. However, the Money Transmission Modernization Act does not remove the need for multiple state licenses. — [K&L Gates](https://www.klgates.com/The-GENIUS-Act-and-Stablecoins-Could-This-Replace-State-Money-Transmitter-Licensing-10-6-2025)

### Inferences
- **Who pays:** fintechs, marketplaces, payroll and remittance companies, and treasury teams of exporters and importers. They pay basis-point fees on volume plus FX spread. The BVNK exit shows strategic acquirers (card networks, PSPs) will pay about $1.5–2B for licensed, multi-region rails. That is the exit model for a well-executed player.
- **Startup-feasible plays:**
  - **(1) Vertical or regional orchestration** (e.g., LatAm or Africa corridors, à la VelaFi and Yellow Card) on licensed partners such as Bridge, Brale or BVNK. Seed-scale cost; low margin; partner dependency risk.
  - **(2) GENIUS compliance and reserve-attestation software** for small and state-regulated issuers: reserve reporting, monthly attestation workflow, AML/sanctions on-chain monitoring. SaaS sold to issuers' CFO and compliance teams. Demand peaks around the Jan 18, 2027 effective date and the Nov 2026 OCC/FDIC rules.
  - **(3) Agent and AI-commerce stablecoin settlement** (Augustus thesis), which is capital-heavy.
- **Moat reality:** MTLs and OCC charters protect incumbents. A startup should rent licenses and plan for take-rate compression as Mastercard, Stripe and Visa bundle the rails.
- **Window:** 6–18 months before final GENIUS rules and network bundling harden. Risk: issuance and payment acceptance are commoditizing fast; an "issuance-in-one-day" claim (Agora) signals this.

### Gaps
- No published take rates or pricing for Bridge, Brale, BVNK or M0. Unit economics are unknown.
- No standalone reserve-attestation startup surfaced. Attestation is currently done by audit firms (not researched).
- Circle's final-charter status is unverified.

## 4. Tokenized stocks / RWAs under the Sept 17, 2026 SEC innovation exemption

### Takeaway
The exemption is a five-year conditional order. It is limited to permissioned AMM/liquidity-pool trading of tokenized NMS stock and offers no Investment Company Act relief. No venue had launched by early Oct 2026; first operational-plan notices are expected "next quarter". Infrastructure leaders are funded transfer-agent and broker-dealer hybrids, and big exchanges are queuing. The startup opening is picks-and-shovels: compliant AMM tech, liquidity provisioning, issuer-consent and objection workflows, oracle and corporate-action data. Running a venue requires broker-dealer and transfer-agent capital.

### Cited Findings
- **The exemption:**
  - The SEC issued two five-year conditional exemptions on Sept 17, 2026.
  - One covers "Tokenized Securities Venues" from the exchange definition. The other gives certain liquidity providers limited dealer-definition relief.
  - Trading is permissioned via AMMs and liquidity pools; a standalone CLOB protocol appears not covered.
  - There is no Investment Company Act relief, so tokenized MMFs are excluded.
  - Listed issuers get a **30-day objection period** before third-party stock tokens list.
  — [Skadden, Sept 2026](https://www.skadden.com/insights/publications/2026/09/sec-innovation-exemption-establishes); [Sullivan & Cromwell](https://www.sullcrom.com/insights/memo/2026/September/SEC-Issues-Innovation-Exemption-for-Tokenized-Securities); [Harvard CorpGov, Sept 25, 2026](https://corpgov.law.harvard.edu/2026/09/25/sec-issues-innovation-exemption-for-tokenized-securities/); [Dechert](https://www.dechert.com/content/dechert/en/knowledge/onpoint/2026/9/sec-issues--innovation-exemption--to-facilitate-trading-of-token.html)
- SEC Crypto Task Force counsel Taylor Lindman expects operational-plan notices in coming months, with first applications possibly "next quarter". This is reported by exchange-blog outlets, a lower-quality source. — [KuCoin news](https://www.kucoin.com/news/flash/u-s-sec-s-innovation-exemption-for-tokenized-stocks-to-see-first-trading-platforms-in-q4-2026)
- Coinbase plans US tokenized stocks when permitted. Robinhood, Kraken and others already offer tokenized stocks overseas (Reuters via American Banker, as cited). — [American Bazaar, Sept 17, 2026](https://americanbazaaronline.com/2026/09/17/sec-gives-tokenized-stock-platforms-five-year-exemption-488381/)
- **Superstate** raised an **$82.5M Series B** (Feb 2026) led by Bain Capital Crypto and Distributed Global. It is an SEC-registered transfer agent. Its "Opening Bell" lets issuers tokenize their own shares; Galaxy is an example. Invesco took over its roughly $900M USTB T-bill fund (Mar 2026), while Superstate keeps tokenization and transfer agency. — [Orrick, Feb 2026](https://www.orrick.com/en/News/2026/02/Superstate-Raises-82-5-Million-Series-B-to-Advance-Tokenized-Investment-Products); [Fortune, Mar 24, 2026](https://fortune.com/2026/03/24/invesco-superstate-ustb/)
- **Dinari** is a transfer agent and broker-dealer that has raised over $22M. On Aug 4, 2026 it launched 724 tokenized US stocks (all of the S&P 500) for US investors, bought with USDC via self-custody wallets. Some analysts describe dShares as OTC derivative-like. — [CoinDesk, Aug 4, 2026](https://www.coindesk.com/business/2026/08/04/dinari-brings-tokenized-u-s-stocks-to-american-investors-as-equity-race-heats-up)
- **Securitize** is described as having a $1.25B SPAC deal and an NYSE partnership, and it powers BlackRock's BUIDL. This comes from an aggregator and was not verified. — [Eco](https://eco.com/support/en/articles/15254023-tokenized-equities-2026-backed-dinari-robinhood)

### Inferences
- **Who pays and what:**
  - Venues pay for AMM, compliance and whitelisting tech.
  - Issuers pay transfer-agent and tokenization fees (Superstate model).
  - Liquidity providers earn spreads and AMM fees under limited dealer relief.
  - Brokers and wallets pay for embedded tokenized-stock APIs (Dinari model).
- **Startup-feasible niches:** issuer-objection and consent workflow, KYC/whitelist identity layers for permissioned pools, corporate-action and dividend oracles, and surveillance/market-integrity tooling for AMM venues. These are SaaS or per-trade fees.
- **Cost:** a transfer-agent registration or broker-dealer adds capital, compliance staff and time. Tooling-only plays are seed-scale.
- **Window:** the order runs 5 years but is revocable by a future Commission. Coinbase, Robinhood, NYSE/ICE and Nasdaq entry will compress venue economics, so B2B tooling is the safer bet.

### Gaps
- No published fees for Superstate or Dinari.
- No startups identified specifically building permissioned-AMM tech for the exemption.
- The 2026 Securitize SPAC and financing status is unverified.

## 5. Prediction-market adjacent: data, analytics, market making, white-label tooling

### Takeaway
The ecosystem layer is forming fast and being absorbed by the platforms. Polymarket bought the API startup Dome (Feb 2026), and Oddpool joined Kalshi after a $3M seed. A dedicated $35M fund (5c(c) Capital) backed by both CEOs targets data, liquidity and compliance startups. Institutional cross-venue tooling is getting Series A money (EDGE Markets, $29.2M). The best exit path for small data and tooling startups is acqui-hire or acquisition by Kalshi or Polymarket. The main risk is platform dependency plus state-versus-CFTC legal fights.

### Cited Findings
- **Platform valuations:**
  - Kalshi raised $1B+ at a $22B valuation. Bloomberg dated it Mar 19, 2026, led by Coatue; another source says a May 2026 Series F, so dates conflict.
  - Kalshi is reportedly in talks at about $40B.
  - Polymarket reportedly seeks about $1B at $15–20B+.
  - ICE completed a $2B commitment to Polymarket.
  — [FOW](https://www.fow.com/insights/kalshi-to-raise-funds-at-40bn-valuation-to-support-new-offerings-report); [TFN](https://techfundingnews.com/kalshi-targets-40b-valuation-nearly-triple-rival-polymarkets-15b-target-as-prediction-markets-split-in-two/); [company.gi](https://company.gi/blog/prediction-markets-institutional-land-grab-2026)
- **5c(c) Capital** (Mar 23, 2026) is raising up to $35M to back about 20 early-stage startups over two years. It focuses on data tools, liquidity provision and compliance systems, and the Kalshi and Polymarket CEOs are investing. — [TechCrunch, Mar 23, 2026](https://techcrunch.com/2026/03/23/despite-bitter-rivalry-kalshi-polymarket-ceos-back-35m-predictions-markets-vc-fund/); [Fortune, Mar 23, 2026](https://fortune.com/2026/03/23/kalshi-polymarket-5cc-capital-prediction-market-fund-raise/)
- **Dome**, a YC-backed unified prediction-market API, was acquired by Polymarket in Feb 2026. It had raised a $4.7M seed plus $500K from YC. — [The Block](https://theblock.co/post/390546/polymarket-buys-fresh-prediction-market-api-startup-dome-marking-second-official-acquisition)
- **Oddpool**, a prediction-market data layer, raised a $3M seed and is joining Kalshi to build institutional data tools. The date is uncertain: June vs Sept 2026. — [Dealroom](https://dealroom.co/news/149005-oddpool-raises-3m-seed-then-joins-kalshi); [The SaaS News](https://thesaasnews.com/news/oddpool-raises-3m-seed)
- **Polysights** raised a $1.5M pre-seed for AI monitoring (insider trading, wallet clustering, anomalies) from YZi Labs, Maven11 and others. — (search snippet; [vcbacked prediction-markets directory](https://www.vcbacked.co/directory/funding/seed/industry/prediction-markets))
- **EDGE Markets** raised a $29.2M Series A led by CoinFund (June 2026). It builds institutional tooling for market makers to move capital across venues from one account. — (search snippet via [Fortune/TechCrunch cluster]; primary not fetched)
- **Pascal** raised a $9M round (Fortune says Series A) led by USV (July 2026). It is a new prediction-market venue challenging Kalshi and Polymarket. — [Fortune, Jul 16, 2026](https://fortune.com/2026/07/16/exclusive-prediction-market-startup-pascal-9-million-heavyweights-kalshi-and-polymarket/)
- Traders are consolidating how they fund Kalshi and Polymarket accounts, an emerging funding and wallet tooling need. — [FinSMEs, Oct 2026](https://www.finsmes.com/2026/10/why-prediction-market-traders-are-consolidating-how-they-fund-kalshi-and-polymarket.html)

### Inferences
- **Models:**
  - **(1) Data and analytics subscriptions** (unified odds feeds, historical data) sold to quant funds, media and sportsbooks. Tiered API pricing.
  - **(2) Surveillance and integrity SaaS** sold to venues and to state regulators and leagues, the Polysights thesis.
  - **(3) Cross-venue execution and market making**, which is capital-intensive and earns spread.
  - **(4) White-label event-contract tooling** for brokers and fintechs wanting embedded markets. This requires a DCM partner (Kalshi) or a CFTC license.
- **Cost:** data and analytics are seed-scale. Market making needs a trading balance sheet. Running a venue requires DCM registration or an acquired DCM.
- **Window:** short, about 12–24 months, before platforms build or buy (Dome, Oddpool precedents).
- **Risks:** platform API terms changes; state AG and gaming-regulator litigation over sports contracts (see prior report); insider-trading scrutiny, which is also a demand driver for surveillance tools.

### Gaps
- No published Kalshi or Polymarket API pricing or partner revenue-share terms found.
- EDGE Markets and Polysights details come from search snippets; primary sources were not fetched.
- No white-label event-contract vendor identified.

## 6. Open banking / Section 1033 uncertainty and OCC trust charters

### Takeaway
The 2024 §1033 rule is enjoined (Oct 29, 2025). The CFPB rewrite went to OIRA on Aug 6, 2026 and would allow bank data-access fees, likely after a free-request threshold. JPMorgan already charges Plaid; one unconfirmed estimate puts this at about $300M/yr. The business opening shifts from "free data pipes" to fee-aware tooling: aggregator abstraction and routing that minimizes per-call fees, consent and permissioning, and bank-side monetization platforms (Akoya-like). Startups dependent on free bank data face cost shocks. On the charter side, OCC national trust charters (conditional approvals in Dec 2025 and Feb 2026) are becoming the stablecoin-era moat, which favors well-capitalized players.

### Cited Findings
- The §1033 rule is enjoined and being rewritten. The NPRM was sent to OIRA on **Aug 6, 2026**. Proposed changes include allowing data-access fees, possibly after a number of free requests, and tightening the "authorized representative" standard. — [PYMNTS, 2026](https://www.pymnts.com/legal/bank-regulation/2026/cfpb-open-banking-rewrite-could-put-data-access-fees-at-center-of-section-1033-fight/); [RiskTemplate, Sept 28, 2026](https://risktemplate.com/blog/2026-09-28-cfpb-section-1033-rewrite-data-access-fees-open-banking-fintech-2026/); [Open Banking Tracker](https://openbankingtracker.com/guides/section-1033-status)
- JPMorgan implemented data-access fees, and in a renewed deal Plaid compensates the bank. One analysis estimates about $300M/yr, which would exceed 75% of Plaid's 2024 revenue; this is unconfirmed. — [Analysis Atlas (estimate)](https://analysis-atlas.com/research/open-banking-financial-data-aggregation-market/); [American Banker](https://www.americanbanker.com/news/on-the-day-of-a-would-be-deadline-open-banking-is-in-flux)
- Akoya told the CFPB that data providers "should be able to charge reasonable fees." — [PYMNTS](https://www.pymnts.com/legal/bank-regulation/2026/cfpb-open-banking-rewrite-could-put-data-access-fees-at-center-of-section-1033-fight/)
- New York introduced bills (Mar 2026) to ban data-access fees at the state level. States are increasingly active on data sharing. — [Consumer Finance Monitor, Jun 26, 2026](https://www.consumerfinancemonitor.com/2026/06/26/open-banking-regulation-in-2026-federal-regulation-resurfaces-as-states-bring-data-sharing-into-focus/)
- Practitioner advice is to build a thin provider-abstraction layer across Plaid, MX, Finicity and Akoya, and to treat fees as a planning variable. — [Open Banking Tracker, 2026](https://www.openbankingtracker.com/blog/best-open-banking-api-providers-developers-2026)
- **OCC trust charters:**
  - Conditional approvals went to Circle, Ripple, BitGo, Fidelity Digital Assets and Paxos (Dec 2025) and to Bridge (Feb 2026).
  - Final approval has no set timeline and requires meeting conditions.
  — [CoinDesk, Feb 17, 2026](https://www.coindesk.com/business/2026/02/17/stripe-s-stablecoin-firm-bridge-wins-initial-approval-of-national-bank-trust-charter); [Payments Dive](https://www.paymentsdive.com/news/stripe-bridge-occ-conditional-approval-national-trust-bank-charter/812425/)

### Inferences
- **Plays:**
  - **(1) Multi-aggregator routing and cost optimization** sold to fintechs: SaaS plus a percentage of fee savings.
  - **(2) Bank-side data-access monetization and API platforms** for community banks that now may charge: rev-share with banks.
  - **(3) Consent and permissioning ledgers** that satisfy the tightened authorized-representative standard and NY-style state rules.
  - **(4) Pay-by-bank as an alternative** that avoids per-pull fees.
- **Charters as a service:** a startup cannot cheaply obtain an OCC charter. The opening is **compliance, BSA/AML and reporting tooling for new trust banks** and "charter-holder-as-partner" programs, where startups rent Bridge's or Paxos's charter as a BaaS-like model.
- **Window:** until the final 1033 rule (2027?) and state laws settle. Risk: fees kill consumer-fintech budgets, shrinking the buyer pool.

### Gaps
- Actual JPM–Plaid fee terms are not public.
- No funded startups identified specifically in 1033-fee optimization or bank-side monetization in 2026.
- Final status of the OCC trust charters (Circle final July 10, 2026?) is unverified.
