# CJCE submission sheet (Wiley Research Exchange, submission.wiley.com)

Copy each block into the matching field. Everything below matches the manuscript text exactly.

## Step 1: Type, title, and abstract

**Article type:** Research Article

**Title:** Safe real-time optimization of a distillation column under feed-composition uncertainty: a comparative study of distribution-free constraint back-offs

**Abstract** (215 words, limit 250):

Real-time optimization (RTO) pushes a distillation column toward its product specifications, so the optimizer must subtract a back-off from any specification it cannot measure online. Data-driven back-offs sized with conformal prediction are attractive because they need no disturbance model, but their guarantee holds on average over operating points, and the optimizer does not choose operating points at random. This study compares six ways of sizing the back-off of a chance-constrained RTO for a rigorous DWSIM Peng-Robinson debutanizer twin under an unmeasured feed-composition disturbance, scoring every deployed setpoint by its exact violation probability over 1000 repeated trials. At the realistic disturbance level, conformal back-offs that are valid on average deploy a setpoint whose violation probability exceeds the 10% target in 67.5% to 100% of trials, and an a posteriori plug-in correction still does so in 32.0%. Certify-then-deploy, a fixed-sequence binomial test of candidate setpoints, and scenario-based sampling-and-discarding keep this rate at or below 2.5% while staying within 0.06% to 0.21% of the oracle profit. A risk-adjusted analysis shows that the unguaranteed back-offs lose money in expectation once off-spec bottoms cost more than 0.017 to 0.032 USD/kg, about 2% to 4% of the product value. The results give a selection rule: use sampling-and-discarding when the plant model fits inside the optimizer, and certify-then-deploy when it does not.

## Step 2: File upload

| File | Designation |
|---|---|
| main.pdf | Main Document |
| Highlights_Most_Relevant_Contributions.docx | Manuscript's Most Relevant Contributions |

LaTeX sources are uploaded only after acceptance. If the system insists on source now: main.tex as Main Document; references.bib, angew.bst, and the four PNG figures as TeX/LaTeX Supplementary File.

## Step 3: Attributes

**Keywords:** chance constraint; conformal prediction; digital twin; distillation; real-time optimization; scenario approach

## Step 4: Authors and institutions

- Bien Don Busico (corresponding author), Mapua Malayan Colleges Mindanao, Davao City, Davao del Sur, Philippines; bienbusico@gmail.com; ORCID 0009-0006-7755-2470

**CRediT roles to tick (12):** Conceptualization; Data curation; Formal analysis; Investigation; Methodology; Project administration; Resources; Software; Validation; Visualization; Writing - original draft; Writing - review & editing. Leave Funding acquisition and Supervision unticked.

## Step 5: Review preferences (suggested reviewers)

### 1. Prashant Mhaskar
- First name: Prashant
- Last name: Mhaskar
- Title: Professor
- Email: mhaskar@mcmaster.ca
- Institution: McMaster University
- Department: Department of Chemical Engineering
- Address: Department of Chemical Engineering, McMaster University, 1280 Main Street West, Hamilton, Ontario L8S 4L7, Canada
- Reason: Expert in data-driven real-time optimization and control of distillation columns (Rodriguez, Mhaskar, and Mahalec, Can. J. Chem. Eng. 2025); well placed to judge the RTO formulation, the DWSIM debutanizer case study, and practical relevance.

### 2. Zukui Li
- First name: Zukui
- Last name: Li
- Title: Professor
- Email: zukui@ualberta.ca
- Institution: University of Alberta
- Department: Department of Chemical and Materials Engineering
- Address: Department of Chemical and Materials Engineering, University of Alberta, 13-271 Donadeo Innovation Centre for Engineering, 9211 116 Street NW, Edmonton, Alberta T6G 2H5, Canada
- Reason: Leading researcher in data-driven chance-constrained and distributionally robust process optimization (AIChE J. 2023, doi:10.1002/aic.18177); well placed to assess the distribution-free back-off constructions and their sampling-based guarantees.

### 3. Kostas Margellos
- First name: Kostas
- Last name: Margellos
- Title: Associate Professor
- Email: kostas.margellos@eng.ox.ac.uk
- Institution: University of Oxford
- Department: Department of Engineering Science
- Address: Department of Engineering Science, University of Oxford, Parks Road, Oxford OX1 3PJ, United Kingdom
- Reason: Expert in scenario optimization and conformal prediction for data-driven decision making (O'Sullivan, Romao, and Margellos, IEEE CDC 2025); well placed to check the statistical guarantees of the conformal, certify-then-deploy, and scenario back-offs.

### 4. Joel Paulson
- First name: Joel
- Last name: Paulson
- Title: Associate Professor
- Email: joel.paulson@wisc.edu
- Institution: University of Wisconsin-Madison
- Department: Department of Chemical and Biological Engineering
- Address: Department of Chemical and Biological Engineering, University of Wisconsin-Madison, Engineering Hall, 1415 Engineering Drive, Madison, WI 53706, USA
- Reason: Developed explicit back-off methods for stochastic predictive control (Paulson and Mesbah, IFAC-PapersOnLine 2018) and works on data-driven optimization under uncertainty; well placed to judge the back-off constructions against the stochastic MPC and RTO literature.

**Swap-ins if the editorial-board check finds a conflict:** Christopher L. E. Swartz (McMaster; swartzc@mcmaster.ca) or Jinfeng Liu (Alberta; jinfeng@ualberta.ca) for RTO; Simone Garatti (Politecnico di Milano; simone.garatti@polimi.it) for scenario methods. Do not pair two reviewers from the same department.

**Opposed reviewers:** none.

## Step 6: Details and comments

- Cover letter: upload Cover_Letter_CJCE.docx (mandatory).
- Previously published or under consideration elsewhere: No.
- Preprint: No.
- Funding: This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.
- Conflict of interest: The author declares no conflict of interest.
- Data availability statement: The data that support the findings of this study are openly available in GitHub at https://github.com/beebzy-droid/IPIS, including the DWSIM campaign data (docs/module3/cjce/data), the scripts that regenerate every figure and table from fixed random seeds, and the evidence files.
- Use of generative AI (answer consistently with the Acknowledgements): The author used Claude (Anthropic; Claude Opus 5.5 and earlier versions), a large language model, to assist with drafting and editing the manuscript text and with writing and debugging parts of the Python analysis and plotting code. The author directed the study, reviewed and tested all outputs, verified every reported number against the regenerated evidence files, and takes full responsibility for the content. No generative AI tool was used to create or alter simulation data or results; the figures were produced by the author's code from the simulation data.
- Ethics approval, patient consent, clinical trial registration, permission to reproduce material: Not applicable.
- Transparent Peer Review: default is to participate; opting out is allowed and does not affect the decision.

## Step 7: Review and submit

Open the system-built proof and confirm: the title and Correspondence block on page 1, the 215-word abstract, all four figures and both tables, and the superscript reference numbers. Then click SUBMIT and save the confirmation email with the manuscript ID.
