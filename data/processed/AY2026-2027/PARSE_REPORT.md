# Parse report, AY2026-2027

Generated 2026-10-27T13:56:04+00:00 from data fetched 2026-10-27T13:22:51+00:00.

## Summary

| Metric | Value |
|---|---|
| courses_total | 666 |
| courses_with_full_details | 306 |
| stubs_not_in_ay | 95 |
| stubs_outside_fetch_scope | 265 |
| available_to_student | 219 |
| with_prereq | 208 |
| with_preclusion | 201 |
| crosscheck_match | 198 |
| crosscheck_mismatch | 31 |
| parse_errors | 0 |
| courses_with_warnings | 14 |
| courses_with_overrides | 0 |

## Cross-check: prerequisiteRule vs NUSMods prereqTree

Both sources are parsed and resolved independently; they should give the same logic.
Matches: 198. Mismatches: 31. Rule but no tree: 9 (CS2101, CS2101X, ES1000, ES2007D, IS2101, SP1541, SP1541X, SP2271, ST1232).

| Course | From prerequisiteRule | From prereqTree | Resolution |
|---|---|---|---|
| CS1231 | none | MA1301X or MA1301 | rule has a pre-university-subject alternative that prereqTree drops |
| CS1231S | none | MA1301X or MA1301 | rule has a pre-university-subject alternative that prereqTree drops |
| CS2309 | ((CS1231 or CS1231S or MA1100 or MA1100T) and (CS2030 or CS2030S or CS2030DE or CS2030HS) and (CS2040 or CS2040S or CS2040HS or CS2040C or CS2040DE)) or CS2113 or CS2113T | (CS1231 or CS1231S or MA1100 or MA1100T) and (((CS2030 or CS2030S or CS2030DE or CS2030HS) and (CS2040 or CS2040S or CS2040HS or CS2040C or CS2040DE)) or CS2113 or CS2113T) | used prereqTree (ambiguous AND/OR) |
| CS4240 | CS3240 | CS3240 and (MA1301 or MA1301X) | rule has a pre-university-subject alternative that prereqTree drops |
| DSA1101 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| DSA4213 | impossible | MA2001 and (MA2104 or MA2311) and (CS2040 or CS2040C or CS2040DE or CS2040HS or CS2040S or ST2137) | rule has a programme/cohort gate that prereqTree drops |
| DSE1101 | impossible | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops; rule has a programme/cohort gate that prereqTree drops |
| ES1531 | impossible | none | rule has a pre-university-subject alternative that prereqTree drops; rule has a programme/cohort gate that prereqTree drops |
| ES2002 | impossible | ES1000 | rule has a pre-university-subject alternative that prereqTree drops; rule has a programme/cohort gate that prereqTree drops |
| ES2531 | impossible | none | rule has a pre-university-subject alternative that prereqTree drops; rule has a programme/cohort gate that prereqTree drops |
| ES2631 | impossible | none | rule has a pre-university-subject alternative that prereqTree drops; rule has a programme/cohort gate that prereqTree drops |
| FAS1101 | impossible | none | rule has a pre-university-subject alternative that prereqTree drops; rule has a programme/cohort gate that prereqTree drops |
| MA1100 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1100T | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1311 | none | MA1301 or MA1301FC or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1312 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1505 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1508E | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1511 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1512 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1513 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1521 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1522 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA1531 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA2001 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA2002 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MA2301 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| MNO2706 | impossible | none | rule has a programme/cohort gate that prereqTree drops |
| PC1101 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| PC2174A | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |
| ST1131 | none | MA1301 or MA1301X | rule has a pre-university-subject alternative that prereqTree drops |

## Parse errors

None.

## Not available to this student

- BN1111 (Biomedical Engineering Principles and Practice I): not offered in any semester in AY2026-2027
- BN2102 (Bioengineering Data Analysis): outside fetch scope (details not downloaded)
- BSP1703 (Managerial Economics): outside fetch scope (details not downloaded)
- BT2101 (Econometrics Modeling for Business Analytics): outside fetch scope (details not downloaded)
- CE2407 (Engineering & Uncertainty Analyses): not offered in any semester in AY2026-2027
- CG2023 (Signals and Systems): outside fetch scope (details not downloaded)
- CN2116 (Chemical Kinetics & Reactor Design): not offered in any semester in AY2026-2027
- CN2122 (Fluid Mechanics): not offered in any semester in AY2026-2027
- CN2122A (Fluid Mechanics): not offered in any semester in AY2026-2027
- CN2125 (Heat & Mass Transfer): not offered in any semester in AY2026-2027
- CN3421 (Process Modeling And Numerical Simulation): not offered in any semester in AY2026-2027
- CS1010J (Programming Methodology): not offered in any semester in AY2026-2027
- CS2030HS (Programming Methodology II): not open to PROGRAMS 0300CSHON
- CS2040HS (Data Structures and Algorithms): not open to PROGRAMS 0300CSHON
- CS2100R (Computer Organisation): not offered in any semester in AY2026-2027
- CS2101X (Effective Communication for Computing Professionals): prerequisite can never be met by this student (programme/cohort gate)
- CS2109HS (Introduction to AI and Machine Learning): not open to PROGRAMS 0300CSHON
- CS2113T (Software Engineering & Object-Oriented Programming): not offered in any semester in AY2026-2027
- CS3220 (Computer Architecture): not offered in any semester in AY2026-2027
- CS3225 (Combinatorial Methods in Bioinformatics): not offered in any semester in AY2026-2027
- CS3226 (Web Programming and Applications): not offered in any semester in AY2026-2027
- DAO2702 (Programming for Business Analytics and AI): outside fetch scope (details not downloaded)
- DAO2702X (Programming for Business Analytics and AI): outside fetch scope (details not downloaded)
- DBA3803 (Predictive Analytics in Business): outside fetch scope (details not downloaded)
- DSA4213 (Natural Language Processing for Data Science): prerequisite can never be met by this student (programme/cohort gate)
- DSC3214 (Introduction To Optimisation): prerequisite can never be met by this student (programme/cohort gate); not offered in any semester in AY2026-2027
- DSE1101 (Introductory Data Science for Economics): prerequisite can never be met by this student (programme/cohort gate)
- EC1101E (Introduction to Economic Analysis): outside fetch scope (details not downloaded)
- EE1111 (Engineering Principles and Practice I): not offered in any semester in AY2026-2027
- EE2012A (Analytical Methods in Electrical and Computer Engineering): not offered in any semester in AY2026-2027
- EE2020 (Digital Fundamentals): not offered in any semester in AY2026-2027
- EE2023 (Signals and Systems): outside fetch scope (details not downloaded)
- EE2024 (Programming for Computer Interfaces): not offered in any semester in AY2026-2027
- EE3207E (Computer Architecture): not offered in any semester in AY2026-2027
- EE3731C (Signal Analytics): outside fetch scope (details not downloaded)
- EE4204E (Computer Networks): not offered in any semester in AY2026-2027
- EE4214 (Real-Time Embedded Systems): not offered in any semester in AY2026-2027
- EE4214E (Real-Time Embedded Systems): not offered in any semester in AY2026-2027
- EE4704E (Introduction to Computer Vision and Image Processing): not offered in any semester in AY2026-2027
- EE5132 (Wireless and Sensor Networks): not offered in any semester in AY2026-2027
- EE5310 (Communication Networking Fundamentals): not offered in any semester in AY2026-2027
- EE6310 (Communication Networking Fundamentals (Advanced)): not offered in any semester in AY2026-2027
- EG2401A (Engineering Professionalism): outside fetch scope (details not downloaded)
- ES1531 (Critical Thinking And Writing): prerequisite can never be met by this student (programme/cohort gate); not offered in any semester in AY2026-2027
- ES2002 (Business Communication for Leaders (BBA)): prerequisite can never be met by this student (programme/cohort gate)
- ES2007D (Professional Communication): prerequisite can never be met by this student (programme/cohort gate); not offered in any semester in AY2026-2027
- ES2531 (Critical Thinking And Writing): prerequisite can never be met by this student (programme/cohort gate); not offered in any semester in AY2026-2027
- ES2631 (Critique and Communication of Thinking and Design): prerequisite can never be met by this student (programme/cohort gate)
- FAS1101 (Writing Academically: Arts and Social Sciences): prerequisite can never be met by this student (programme/cohort gate)
- GEK1549 (Critical Thinking And Writing): not offered in any semester in AY2026-2027
- GET1021 (Critical Thinking And Writing): not offered in any semester in AY2026-2027
- IE3101 (Statistics For Engineering Applications): outside fetch scope (details not downloaded)
- IS2103 (Enterprise Systems Server-side Design and Development): not offered in any semester in AY2026-2027
- IS3106 (Enterprise Systems Interface Design and Development): not offered in any semester in AY2026-2027
- IS4240 (Business Intelligence Systems): not offered in any semester in AY2026-2027
- IT2002 (Database Technology and Management): not open to PROGRAMS 0300CSHON
- IT3010 (Data Management for Business Analytics): outside fetch scope (details not downloaded)
- IT3011 (Introduction to Machine Learning and Applications): not offered in any semester in AY2026-2027
- LSM2241 (Introductory Bioinformatics): not offered in any semester in AY2026-2027
- MA1311 (Matrix Algebra): not offered in any semester in AY2026-2027
- MA1312 (Calculus with Applications): not offered in any semester in AY2026-2027
- MA1531 (Calculus for Data Science): not open to PROGRAMS 0300CSHON
- MA2001 (Linear Algebra I): not open to PROGRAMS 0300CSHON
- MA2002 (Calculus): not open to PROGRAMS 0300CSHON
- MA2101 (Linear Algebra II): outside fetch scope (details not downloaded)
- MA2101S (Linear Algebra II (S)): outside fetch scope (details not downloaded)
- MA2202 (Algebra I): outside fetch scope (details not downloaded)
- MA2202S (Algebra I (S)): outside fetch scope (details not downloaded)
- MA2213 (Numerical Analysis I): outside fetch scope (details not downloaded)
- MA2214 (Combinatorics and Graphs I): outside fetch scope (details not downloaded)
- MA2288 (Basic UROPS in Mathematics I): outside fetch scope (details not downloaded)
- MA2288R (Basic UROPS in Mathematics I (REx)): outside fetch scope (details not downloaded)
- MA2289 (Basic UROPS in Mathematics II): outside fetch scope (details not downloaded)
- MA2289R (Basic UROPS in Mathematics II (REx)): outside fetch scope (details not downloaded)
- MA2301 (Basic Applied Mathematics): not offered in any semester in AY2026-2027
- MA2310 (FOS Undergraduate Professional Internship Programme 1ST): outside fetch scope (details not downloaded)
- MA2312U (FOS Undergraduate Professional Internship Programme 2S1): outside fetch scope (details not downloaded)
- MA2313 (FOS Undergraduate Professional Internship Programme 2S2): outside fetch scope (details not downloaded)
- MA2401 (Introductory Mathematics with R): outside fetch scope (details not downloaded)
- MA3201 (Algebra II): outside fetch scope (details not downloaded)
- MA3205 (Set Theory): outside fetch scope (details not downloaded)
- MA3209 (Metric and Topological Spaces): outside fetch scope (details not downloaded)
- MA3210 (Mathematical Analysis II): outside fetch scope (details not downloaded)
- MA3211 (Complex Analysis I): outside fetch scope (details not downloaded)
- MA3211S (Complex Analysis I (S)): outside fetch scope (details not downloaded)
- MA3220 (Ordinary Differential Equations): outside fetch scope (details not downloaded)
- MA3233 (Combinatorics and Graphs II): outside fetch scope (details not downloaded)
- MA3238 (Stochastic Processes I): outside fetch scope (details not downloaded)
- MA3238S (Stochastic Processes I (S)): outside fetch scope (details not downloaded)
- MA3264 (Mathematical Modelling): outside fetch scope (details not downloaded)
- MA3265 (Introduction to Number Theory): outside fetch scope (details not downloaded)
- MA3288 (Advanced UROPS in Mathematics I): outside fetch scope (details not downloaded)
- MA3288R (Advanced UROPS in Mathematics I (REx)): outside fetch scope (details not downloaded)
- MA3289 (Advanced UROPS in Mathematics II): outside fetch scope (details not downloaded)
- MA3310 (FOS Undergraduate Professional Internship Programme 2ST): outside fetch scope (details not downloaded)
- MA3312 (FOS Undergraduate Professional Internship Programme 3S1): outside fetch scope (details not downloaded)
- MA3313 (FOS Undergraduate Professional Internship Programme 3S2): outside fetch scope (details not downloaded)
- MA4198 (Mathematics Capstone Project): outside fetch scope (details not downloaded)
- MA4203 (Galois Theory): outside fetch scope (details not downloaded)
- MA4207 (Mathematical Logic): outside fetch scope (details not downloaded)
- MA4211 (Functional Analysis): outside fetch scope (details not downloaded)
- MA4221 (Partial Differential Equations): outside fetch scope (details not downloaded)
- MA4229 (Fourier Analysis and Approximation): outside fetch scope (details not downloaded)
- MA4230 (Matrix Computation): outside fetch scope (details not downloaded)
- MA4233 (Dynamical Systems): outside fetch scope (details not downloaded)
- MA4235 (Topics in Graph Theory): outside fetch scope (details not downloaded)
- MA4251 (Stochastic Processes II): outside fetch scope (details not downloaded)
- MA4254 (Discrete Optimization): outside fetch scope (details not downloaded)
- MA4255 (Numerical Methods in Differential Equations): outside fetch scope (details not downloaded)
- MA4261 (Information and Coding Theory): outside fetch scope (details not downloaded)
- MA4262 (Measure and Integration): outside fetch scope (details not downloaded)
- MA4264 (Game Theory): outside fetch scope (details not downloaded)
- MA4266 (Introduction to Algebraic Topology): outside fetch scope (details not downloaded)
- MA4270 (Data Modelling and Computation): outside fetch scope (details not downloaded)
- MA4273 (Algebraic Geometry of Curves and Surfaces): outside fetch scope (details not downloaded)
- MA4275 (Mathematics of Reinforcement Learning): outside fetch scope (details not downloaded)
- MA4276 (Theory of Algebraic Numbers): outside fetch scope (details not downloaded)
- MA4288O (Undergraduate Project in Mathematics): outside fetch scope (details not downloaded)
- MA4288P (Undergraduate Project in Mathematics): outside fetch scope (details not downloaded)
- MA4310 (FOS Undergraduate Professional Internship Programme 3ST): outside fetch scope (details not downloaded)
- MA4312 (FOS Undergraduate Professional Internship Programme 4S1): outside fetch scope (details not downloaded)
- MA4313 (FOS Undergraduate Professional Internship Programme 4S2): outside fetch scope (details not downloaded)
- MA5198 (Graduate Seminar Course in Mathematics): outside fetch scope (details not downloaded)
- MA5202 (Number Theory): outside fetch scope (details not downloaded)
- MA5204 (Commutative and Homological Algebra): outside fetch scope (details not downloaded)
- MA5205 (Graduate Analysis I): outside fetch scope (details not downloaded)
- MA5206 (Graduate Analysis II): outside fetch scope (details not downloaded)
- MA5210 (Differentiable Manifolds): outside fetch scope (details not downloaded)
- MA5213 (Advanced Partial Differential Equations): outside fetch scope (details not downloaded)
- MA5216 (Differential Geometry): outside fetch scope (details not downloaded)
- MA5217 (Graduate Complex Analysis): outside fetch scope (details not downloaded)
- MA5218 (Representation Theory): outside fetch scope (details not downloaded)
- MA5219 (Logic and Foundation of Mathematics I): outside fetch scope (details not downloaded)
- MA5222 (Ergodic Theory): outside fetch scope (details not downloaded)
- MA5232 (Modeling and Numerical Simulations): outside fetch scope (details not downloaded)
- MA5233 (Computational Mathematics): outside fetch scope (details not downloaded)
- MA5243 (Advanced Mathematical Programming): outside fetch scope (details not downloaded)
- MA5248 (Stochastic Analysis in Mathematical Finance): outside fetch scope (details not downloaded)
- MA5249 (Stochastic Processes and Algorithms): outside fetch scope (details not downloaded)
- MA5251 (Spectral Methods and Applications): outside fetch scope (details not downloaded)
- MA5252 (Methods of Applied Mathematics): outside fetch scope (details not downloaded)
- MA5259 (Introductory Probability): outside fetch scope (details not downloaded)
- MA5260 (Advanced Probability): outside fetch scope (details not downloaded)
- MA5266 (Optimization): outside fetch scope (details not downloaded)
- MA5270 (Game Theory and applications): outside fetch scope (details not downloaded)
- MA5271 (Introduction to Computational Mathematics): outside fetch scope (details not downloaded)
- MA5272 (Mathematical Underpinnings of Data Science): outside fetch scope (details not downloaded)
- MA5401 (Graduate Internship in Mathematics I): outside fetch scope (details not downloaded)
- MA5402 (Graduate Internship in Mathematics II): outside fetch scope (details not downloaded)
- MA6202 (Approximate Subgroups): outside fetch scope (details not downloaded)
- MA6211 (Topics in Geometry and Topology I): outside fetch scope (details not downloaded)
- MA6225 (Topics in Machine Learning): outside fetch scope (details not downloaded)
- MA6291 (Topics in Mathematics I): outside fetch scope (details not downloaded)
- ME1102 (Engineering Principles and Practice I): not offered in any semester in AY2026-2027
- ME2104 (Engineering Principles and Practice II): not offered in any semester in AY2026-2027
- ME2143E (Sensors and Actuators): not offered in any semester in AY2026-2027
- MNO2706 (Business Communication for Leaders (ACC)): prerequisite can never be met by this student (programme/cohort gate); not offered in any semester in AY2026-2027
- NM1101E (Communications, New Media and Society): outside fetch scope (details not downloaded)
- NM1101X (Communications, New Media and Society): outside fetch scope (details not downloaded)
- NM2101 (Theories of Communications and New Media): outside fetch scope (details not downloaded)
- NM2103 (Quantitative Research Methods): outside fetch scope (details not downloaded)
- NM2104 (Qualitative Communication Research Methods): outside fetch scope (details not downloaded)
- NM2105 (Communicative Competence in Action): outside fetch scope (details not downloaded)
- NM2209 (Social Psychology of New Media): outside fetch scope (details not downloaded)
- NM2219 (Principles of Communication Management): outside fetch scope (details not downloaded)
- NM2220 (Introduction to Media Writing): outside fetch scope (details not downloaded)
- NM2223 (Media Law and Policy): outside fetch scope (details not downloaded)
- NM2226 (Introduction to Visual Cultural Analytics): outside fetch scope (details not downloaded)
- NM2227 (Understanding Visual Culture): outside fetch scope (details not downloaded)
- NM2228 (Data Intelligence for Social Applications): outside fetch scope (details not downloaded)
- NM3205 (Digital Media Cultures): outside fetch scope (details not downloaded)
- NM3217 (Principles of Visual Communication Design): outside fetch scope (details not downloaded)
- NM3219 (Writing for Communication Management): outside fetch scope (details not downloaded)
- NM3221 (Mobile Interaction Design): not offered in any semester in AY2026-2027
- NM3230 (Digital Storytelling): outside fetch scope (details not downloaded)
- NM3241 (Cultural Studies: Theory and Practice): outside fetch scope (details not downloaded)
- NM3244 (Consulting as a Communication & Career Skill): outside fetch scope (details not downloaded)
- NM3245 (Managing Arts and Cultural Events): outside fetch scope (details not downloaded)
- NM3246 (Mobile Storytelling for Social Impact): outside fetch scope (details not downloaded)
- NM3247 (Digital Economies): outside fetch scope (details not downloaded)
- NM3248 (Communications, Culture, and Sustainability): outside fetch scope (details not downloaded)
- NM3249 (Digital News Writing and Data Analysis): outside fetch scope (details not downloaded)
- NM3250 (Media, City and Public Culture): outside fetch scope (details not downloaded)
- NM3251 (Media Industries in the Global Age): outside fetch scope (details not downloaded)
- NM3252 (Communicating Risk and Crisis in the Digital Age): outside fetch scope (details not downloaded)
- NM3253 (Fandoms to Algorithms: K-Pop, Data and Culture): outside fetch scope (details not downloaded)
- NM3254 (Artificial Intelligence, Algorithms and Governance): outside fetch scope (details not downloaded)
- NM3255 (AI-Mediated Communication): outside fetch scope (details not downloaded)
- NM3550C (CNM Internship Programme): outside fetch scope (details not downloaded)
- NM3550Y (Communications & New Media Internship): outside fetch scope (details not downloaded)
- NM3551 (FASS Undergraduate Research Opportunity (UROP)): outside fetch scope (details not downloaded)
- NM3551R (FASS Undergraduate Research Opportunity (UROP)): outside fetch scope (details not downloaded)
- NM4206 (Media Policy and Regulation): outside fetch scope (details not downloaded)
- NM4207 (Managing Communication Campaigns): outside fetch scope (details not downloaded)
- NM4208 (Strategic Communication Design): outside fetch scope (details not downloaded)
- NM4212 (Race, Media, and Representation): outside fetch scope (details not downloaded)
- NM4230 (Communications for Social Change): outside fetch scope (details not downloaded)
- NM4231 (Digital Media Storytelling Strategies): outside fetch scope (details not downloaded)
- NM4242 (Critical Perspectives on Technology): outside fetch scope (details not downloaded)
- NM4244 (Sex in the Media): outside fetch scope (details not downloaded)
- NM4245 (Political Communication): outside fetch scope (details not downloaded)
- NM4247 (Creative Writing in the Marketplace): outside fetch scope (details not downloaded)
- NM4249 (Media & Audiences): outside fetch scope (details not downloaded)
- NM4255 (Social Media and Computational Communication): outside fetch scope (details not downloaded)
- NM4257 (Multiplatform Advertising Strategies): outside fetch scope (details not downloaded)
- NM4258 (Health Communication): outside fetch scope (details not downloaded)
- NM4259HM (Mobile Interaction Design): prerequisite can never be met by this student (programme/cohort gate); not offered in any semester in AY2026-2027
- NM4260HM (Game Design): prerequisite can never be met by this student (programme/cohort gate); not offered in any semester in AY2026-2027
- NM4401 (Honours Thesis): outside fetch scope (details not downloaded)
- NM4401HM (Honours Thesis): outside fetch scope (details not downloaded)
- NM4660 (Independent Study): outside fetch scope (details not downloaded)
- NM4660HM (Independent Study): outside fetch scope (details not downloaded)
- NTW2006 (Human Trafficking and Labour Migration): outside fetch scope (details not downloaded)
- NTW2008 (Power, Space and Pleasure): outside fetch scope (details not downloaded)
- NTW2010 (Sites of Tourism): outside fetch scope (details not downloaded)
- NTW2018 (Danger and Security): outside fetch scope (details not downloaded)
- NTW2029 (Evolutionary Psychology and Art): outside fetch scope (details not downloaded)
- NTW2032 (Identity, Death, and Immortality): outside fetch scope (details not downloaded)
- NTW2034 (Wild and Simple: Living and Thinking Sustainably): outside fetch scope (details not downloaded)
- NTW2035 (Art and the Attention Economy): outside fetch scope (details not downloaded)
- NTW2036 (Space, Place and the Human Experience): outside fetch scope (details not downloaded)
- NTW2037 (Absences: Beyond the Edges of the Material World): outside fetch scope (details not downloaded)
- NTW2038 (Screening Historical Trauma): outside fetch scope (details not downloaded)
- NTW2040 (The Limits of Money): outside fetch scope (details not downloaded)
- NTW2041 (The Popularity of Korean Culture): outside fetch scope (details not downloaded)
- NTW2042 (Illusions and Hallucinations: Appearance and Reality): outside fetch scope (details not downloaded)
- PC1432 (Physics IIE): not offered in any semester in AY2026-2027
- PC1432X (Physics IIE): not offered in any semester in AY2026-2027
- PC2134 (Mathematical Mtds in Physics I): not offered in any semester in AY2026-2027
- RVX1000 (Citizen Speak: Persuasion and Polarization in Society): outside fetch scope (details not downloaded)
- RVX1001 (Science Fiction and Society): outside fetch scope (details not downloaded)
- RVX1003 (Print to Screen: Analysing Film Adaptation): outside fetch scope (details not downloaded)
- RVX1004 (Cultural Expressions of Science, Technology and Warfare): outside fetch scope (details not downloaded)
- RVX1005 (Intersectionality, Identity and Inequality in Asia): outside fetch scope (details not downloaded)
- RVX1006 (Storying Sustainability: Dodos, Condos & Tornadoes): outside fetch scope (details not downloaded)
- SA4101 (Software Analysis and Design): outside fetch scope (details not downloaded)
- SA4101C (Software Analysis and Design): outside fetch scope (details not downloaded)
- SA4104 (Digital Product Management): outside fetch scope (details not downloaded)
- SA4105 (Web Application Development): outside fetch scope (details not downloaded)
- SA4105C (Web Application Development): outside fetch scope (details not downloaded)
- SA4106 (AD Project): outside fetch scope (details not downloaded)
- SA4107 (Industrial Attachment Project): outside fetch scope (details not downloaded)
- SA4108 (Mobile Application Development): outside fetch scope (details not downloaded)
- SA4110 (Machine Learning Application Development): outside fetch scope (details not downloaded)
- SA4110C (Machine Learning Application Development): outside fetch scope (details not downloaded)
- SA4111 (Agile Software Delivery): outside fetch scope (details not downloaded)
- ST1232 (Statistics for Life Sciences): not offered in any semester in AY2026-2027
- ST2137 (Statistical Computing and Programming): outside fetch scope (details not downloaded)
- ST2288 (Basic UROPS in Statistics and Applied Probability I): outside fetch scope (details not downloaded)
- ST2288R (Basic UROPS in Statistics and Applied Probability I (REx)): outside fetch scope (details not downloaded)
- ST2289 (Basic UROPS in Statistics and Applied Probability II): outside fetch scope (details not downloaded)
- ST2289R (Basic UROPS in Statistics and Applied Probability II (REx)): outside fetch scope (details not downloaded)
- ST2310 (FOS Undergraduate Professional Internship Programme 1ST): outside fetch scope (details not downloaded)
- ST2312 (FOS Undergraduate Professional Internship Programme 2S1): outside fetch scope (details not downloaded)
- ST2313 (FOS Undergraduate Professional Internship Programme 2S2): outside fetch scope (details not downloaded)
- ST3232 (Design & Analysis of Experiments): outside fetch scope (details not downloaded)
- ST3236 (Stochastic Processes I): outside fetch scope (details not downloaded)
- ST3239 (Survey Methodology): outside fetch scope (details not downloaded)
- ST3244 (Demographic Methods): outside fetch scope (details not downloaded)
- ST3246 (Statistical Models for Actuarial Science): outside fetch scope (details not downloaded)
- ST3247 (Simulation): outside fetch scope (details not downloaded)
- ST3288 (Advanced UROPS in Statistics & Applied Probability I): outside fetch scope (details not downloaded)
- ST3288R (Advanced UROPS in Statistics & Applied Probability I (REx)): outside fetch scope (details not downloaded)
- ST3289 (Advanced UROPS in Statistics & Applied Probability II): outside fetch scope (details not downloaded)
- ST3289R (Advanced UROPS in Statistics & Applied Probability II (REx)): outside fetch scope (details not downloaded)
- ST3310 (FOS Undergraduate Professional Internship Programme 2ST): outside fetch scope (details not downloaded)
- ST3311 (Undergraduate Professional Internship Programme): outside fetch scope (details not downloaded)
- ST3312 (FOS Undergraduate Professional Internship Programme 3S1): outside fetch scope (details not downloaded)
- ST3313 (FOS Undergraduate Professional Internship Programme 3S2): outside fetch scope (details not downloaded)
- ST4199 (Honours Project in Statistics): outside fetch scope (details not downloaded)
- ST4231 (Computer Intensive Statistical Methods): outside fetch scope (details not downloaded)
- ST4233 (Linear Models): outside fetch scope (details not downloaded)
- ST4234 (Bayesian Statistics): outside fetch scope (details not downloaded)
- ST4238 (Stochastic Processes II): outside fetch scope (details not downloaded)
- ST4245 (Statistical Methods for Finance): outside fetch scope (details not downloaded)
- ST4250 (Multivariate Statistical Analysis): outside fetch scope (details not downloaded)
- ST4253 (Applied Time Series Analysis): outside fetch scope (details not downloaded)
- ST4288 (Honours Project in Statistics): outside fetch scope (details not downloaded)
- ST4299 (Applied Project in Statistics): outside fetch scope (details not downloaded)
- ST4310 (FOS Undergraduate Professional Internship Programme 3ST): outside fetch scope (details not downloaded)
- ST4312 (FOS Undergraduate Professional Internship Programme 4S1): outside fetch scope (details not downloaded)
- ST4313 (FOS Undergraduate Professional Internship Programme 4S2): outside fetch scope (details not downloaded)
- ST5188 (Applied Data Science Project): outside fetch scope (details not downloaded)
- ST5199 (Coursework Track Ii Project): outside fetch scope (details not downloaded)
- ST5201 (Statistical Foundations of Data Science): outside fetch scope (details not downloaded)
- ST5201X (Statistical Foundations of Data Science): outside fetch scope (details not downloaded)
- ST5202 (Applied Regression Analysis): outside fetch scope (details not downloaded)
- ST5202X (Applied Regression Analysis): outside fetch scope (details not downloaded)
- ST5203 (Design of Experiments): outside fetch scope (details not downloaded)
- ST5207 (Nonparametric Regression): outside fetch scope (details not downloaded)
- ST5209X (Analysis Of Time Series Data): outside fetch scope (details not downloaded)
- ST5211X (Sampling from Finite Populations): outside fetch scope (details not downloaded)
- ST5212 (Survival Analysis): outside fetch scope (details not downloaded)
- ST5213 (Advanced Categorical Data Analysis): outside fetch scope (details not downloaded)
- ST5218 (Advanced Statistical Methods in Finance): outside fetch scope (details not downloaded)
- ST5221 (Stochastic Processes and Applications): outside fetch scope (details not downloaded)
- ST5225 (Statistical Analysis of Networks): outside fetch scope (details not downloaded)
- ST5226 (Spatial Statistics): outside fetch scope (details not downloaded)
- ST5227 (Applied Statistical Learning): outside fetch scope (details not downloaded)
- ST5229 (Deep Learning in Data Analytics): outside fetch scope (details not downloaded)
- ST5230 (Applied Natural Language Processing): outside fetch scope (details not downloaded)
- ST5290 (Data Science Industry Project): outside fetch scope (details not downloaded)
- ST6101 (Advanced Statistical Theory): outside fetch scope (details not downloaded)
- ST6102 (Advanced Statistical Theory II): outside fetch scope (details not downloaded)
- ST6103 (Advanced Probability Theory): outside fetch scope (details not downloaded)
- ST6104 (Statistical Models): outside fetch scope (details not downloaded)
- ST6105 (Computational Statistics): outside fetch scope (details not downloaded)
- ST6120 (Graduate Seminar Course): outside fetch scope (details not downloaded)
- ST6242 (Topics II): outside fetch scope (details not downloaded)
- STR1000 (Career Compass Starter Workshops): outside fetch scope (details not downloaded)
- STR2000 (Career Compass Starter Clinics): outside fetch scope (details not downloaded)
- TCX2004 (Introduction to Application Development): outside fetch scope (details not downloaded)
- TEE2003 (Advanced Mathematics for Engineers): outside fetch scope (details not downloaded)
- TEE2023 (Signals and Systems): outside fetch scope (details not downloaded)
- TEE2028 (Microcontroller Programming and Interfacing): outside fetch scope (details not downloaded)
- TEE2101 (Programming Methodology): outside fetch scope (details not downloaded)
- TEE3207 (Computer Architecture): not offered in any semester in AY2026-2027
- TEE4214 (Real-Time Embedded Systems): not offered in any semester in AY2026-2027
- TEE4704 (Introduction to Computer Vision and Image Processing): not offered in any semester in AY2026-2027
- TME2143 (Sensors and Actuators): not offered in any semester in AY2026-2027
- TTG1401 (Engineering Mathematics I): outside fetch scope (details not downloaded)
- UTW1001A (Identities and Ideas in Modern Market-Driven Societies): outside fetch scope (details not downloaded)
- UTW1001AA (Amusing Ourselves to Death? Discerning the Digital Deluge): outside fetch scope (details not downloaded)
- UTW1001C (At the Edges of the Law: Ethics, Morality and Society): outside fetch scope (details not downloaded)
- UTW1001I (Science and popular narratives): outside fetch scope (details not downloaded)
- UTW1001J (How do we frame the Climate Crisis?): outside fetch scope (details not downloaded)
- UTW1001K (Meaning of Home and Identity in the Diaspora): outside fetch scope (details not downloaded)
- UTW1001P (Heroes): outside fetch scope (details not downloaded)
- UTW1001Q (English, Singlish and intercultural communication): outside fetch scope (details not downloaded)
- UTW1001T (How Rich Should Anyone Be?): outside fetch scope (details not downloaded)
- UTW1001V (Am I Who I Am? Knowledge, Language and Identity): outside fetch scope (details not downloaded)
- UTW1001X (Ecospirituality: Religion, Nature, Culture): outside fetch scope (details not downloaded)
- YCC1122 (Quantitative Reasoning): not offered in any semester in AY2026-2027
- YSC1212 (Introduction to Computer Science): not offered in any semester in AY2026-2027
- YSC1213 (General Physics): not offered in any semester in AY2026-2027
- YSC1216 (Calculus): not offered in any semester in AY2026-2027
- YSC2203 (Classical Mechanics): not offered in any semester in AY2026-2027
- YSC2209 (Proof): not offered in any semester in AY2026-2027
- YSC2221 (Introduction to Python): not offered in any semester in AY2026-2027
- YSC2229 (Introductory Data Structures and Algorithms): not offered in any semester in AY2026-2027
- YSC2232 (Linear Algebra): not offered in any semester in AY2026-2027
- YSC2239 (Introduction to Data Science): not offered in any semester in AY2026-2027
- YSC2243 (Probability): not offered in any semester in AY2026-2027
- YSC2252 (Multivariable Calculus): not offered in any semester in AY2026-2027
- YSC3203 (Advanced Algorithms and Data Structures): not offered in any semester in AY2026-2027
- YSC3206 (Introduction to Real Analysis): not offered in any semester in AY2026-2027
- YSC3217 (Programming Operating Systems, Interfaces & eXtras): not offered in any semester in AY2026-2027
- YSC3232 (Software Engineering): not offered in any semester in AY2026-2027
- YSC4216 (Machine Learning): not offered in any semester in AY2026-2027
- YSS1203 (Principles of Economics): not offered in any semester in AY2026-2027
- YSS2203 (Intermediate Microeconomics): not offered in any semester in AY2026-2027
- YSS2211 (Econometrics): not offered in any semester in AY2026-2027

## Warnings (spot-check these first)

- CS2040HS: preclusion rule uses OR; read as 'any clause blocks'
- CS2100: preclusion rule uses OR; read as 'any clause blocks'
- CS2100HS: preclusion rule uses OR; read as 'any clause blocks'
- CS2106: preclusion rule uses OR; read as 'any clause blocks'
- CS2309: prerequisiteRule mixes AND/OR without brackets; using NUSMods prereqTree reading. Usual-precedence reading was: ((CS1231 or CS1231S or MA1100 or MA1100T) and (CS2030 or CS2030S or CS2030DE or CS2030HS) and (CS2040 or CS2040S or CS2040HS or CS2040C or CS2040DE)) or CS2113 or CS2113T
- CS5446: preclusion rule uses OR; read as 'any clause blocks'
- CS5462: preclusion rule uses OR; read as 'any clause blocks'
- CS5477: preclusion rule uses OR; read as 'any clause blocks'
- EE4211: preclusion rule uses OR; read as 'any clause blocks'
- EE4212: preclusion rule uses OR; read as 'any clause blocks'
- EE4704: preclusion rule uses OR; read as 'any clause blocks'
- EE5132: preclusion rule uses OR; read as 'any clause blocks'
- EE5310: preclusion rule uses OR; read as 'any clause blocks'
- YSC4216: preclusion rule uses OR; read as 'any clause blocks'

## Asymmetric preclusions

A lists B as a preclusion but B (in this AY) does not list A. Treated as mutual anyway.

BT1101 → DSA1101, BT1101 → DSE1101, BT1101 → ST1131, BT1101HS → BT1101, BT1101HS → DSA1101, BT1101HS → DSE1101, BT1101HS → EC2303, BT1101HS → ST1131, BT4240 → IS4240, CE2407A → CE2407, CE2407B → CE2407, CG1111A → BN2111, CG1111A → ESP2111, CG1111A → ME2104, CG1111A → ME2105, CG2028 → CS2100, CG3201 → BT4240, CG3201 → DMX1401AI, CG3201 → DMX1501AI, CG3207 → TEE3207, CS2030HS → CS2030DE, CS2040HS → CS2040DE, CS2100DE → CS2100R, CS2100HS → CG2028, CS2100HS → CS2100DE, CS2100HS → EE2028, CS2101 → CS2103, CS2101 → CS2113, CS2101X → CS2103, CS2101X → CS2103T, CS2101X → CS2113, CS2101X → CS2113T, CS2101X → ES2002, CS2101X → ES2007D, CS2101X → IS2101, CS2103DE → CS2103R, CS2103T → ES2002, CS2103T → ES2007D, CS2106 → EE4214, CS2109HS → CG3201, CS2109HS → DMX1401AI, CS2109HS → EE2211, CS2109S → DMX1401AI, CS2109S → EE2211, CS2113T → ES2002, CS2113T → ES2007D, CS2113T → IS2101, CS3244 → DMX1401AI, CS3244 → EE3703, CS4263 → CS2109S, CS4263 → CS3243, CS4263 → CS3263, CS4330 → CS3225, CS5246 → DSA4213, CS5422 → EE5132, DSC3214 → IE2110, EC2303 → SA4101, EC2303 → SA4101C, EC2303 → SA4104, EC2303 → SA4105, EC2303 → SA4105C, EC2303 → SA4106, EC2303 → SA4107, EC2303 → SA4108, EC2303 → SA4110, EC2303 → SA4110C, EC2303 → SA4111, EC2303 → ST1131, EC2303 → ST2132, EC2303 → ST2137, EC2303 → ST2288, EC2303 → ST2288R, EC2303 → ST2289, EC2303 → ST2289R, EC2303 → ST2310, EC2303 → ST2312, EC2303 → ST2313, EC2303 → ST3131, EC2303 → ST3232, EC2303 → ST3236, EC2303 → ST3239, EC2303 → ST3244, EC2303 → ST3246, EC2303 → ST3247, EC2303 → ST3248, EC2303 → ST3288, EC2303 → ST3288R, EC2303 → ST3289, EC2303 → ST3289R, EC2303 → ST3310, EC2303 → ST3311, EC2303 → ST3312, EC2303 → ST3313, EC2303 → ST4199, EC2303 → ST4231, EC2303 → ST4233, EC2303 → ST4234, EC2303 → ST4238, EC2303 → ST4245, EC2303 → ST4248, EC2303 → ST4250, EC2303 → ST4253, EC2303 → ST4288, EC2303 → ST4299, EC2303 → ST4310, EC2303 → ST4312, EC2303 → ST4313, EE1111A → BN1111, EE1111A → EE1111, EE1111A → ESP1111, EE1111A → ME1102, EE1111A → ME2105, EE1111A → RB2101, EE2012 → CE2407A, EE2012 → ST2131, EE2012 → ST2334, EE2012A → ST2131, EE2012A → ST2334, EE2028 → EE2024, EE2111A → ESP2111, EE2111A → ME2104, EE2111A → ME2105, EE2213 → CS2109S, EE4204 → CEG5101, EE4204 → CS2105, EE4204 → EE5310, EE4204 → EE6310, EE4204 → TEE4204, EE4204E → CS2105, EE4204E → CS3103, EE4211 → IT3011, EE4214 → EE4214E, EE4214E → TIC2401, EE4704 → TEE4704, EE4802 → IT3011, EE5132 → CS4222, EE5132 → EE5023, EE5132 → EE5024, EE5310 → EE6310, ES1531 → GEK1549, ES1531 → GET1021, ES1531 → UTW1001A, ES1531 → UTW1001AA, ES1531 → UTW1001C, ES1531 → UTW1001I, ES1531 → UTW1001J, ES1531 → UTW1001K, ES1531 → UTW1001P, ES1531 → UTW1001Q, ES1531 → UTW1001T, ES1531 → UTW1001V, ES1531 → UTW1001X, ES2002 → NTW2006, ES2002 → NTW2008, ES2002 → NTW2010, ES2002 → NTW2018, ES2002 → NTW2029, ES2002 → NTW2032, ES2002 → NTW2034, ES2002 → NTW2035, ES2002 → NTW2036, ES2002 → NTW2037, ES2002 → NTW2038, ES2002 → NTW2040, ES2002 → NTW2041, ES2002 → NTW2042, ES2531 → GEK1549, ES2531 → GET1021, ES2531 → UTW1001A, ES2531 → UTW1001AA, ES2531 → UTW1001C, ES2531 → UTW1001I, ES2531 → UTW1001J, ES2531 → UTW1001K, ES2531 → UTW1001P, ES2531 → UTW1001Q, ES2531 → UTW1001T, ES2531 → UTW1001V, ES2531 → UTW1001X, ES2631 → ES1531, ES2631 → ES2531, ES2631 → GEK1549, ES2631 → GET1021, ES2631 → UTW1001A, ES2631 → UTW1001AA, ES2631 → UTW1001C, ES2631 → UTW1001I, ES2631 → UTW1001J, ES2631 → UTW1001K, ES2631 → UTW1001P, ES2631 → UTW1001Q, ES2631 → UTW1001T, ES2631 → UTW1001V, ES2631 → UTW1001X, ESP1111 → ME1102, FAS1101 → ES1531, FAS1101 → ES2631, FAS1101 → GEK1549, FAS1101 → GET1021, FAS1101 → RVX1000, FAS1101 → RVX1001, FAS1101 → RVX1003, FAS1101 → RVX1004, FAS1101 → RVX1005, FAS1101 → RVX1006, FAS1101 → UTW1001A, FAS1101 → UTW1001AA, FAS1101 → UTW1001C, FAS1101 → UTW1001I, FAS1101 → UTW1001J, FAS1101 → UTW1001K, FAS1101 → UTW1001P, FAS1101 → UTW1001Q, FAS1101 → UTW1001T, FAS1101 → UTW1001V, FAS1101 → UTW1001X, IE2110 → MA3236, IE4213 → CS3244, IE4213 → EE4211, IE4213 → IT3011, IS3106 → CS3226, IT3011 → CS3264, IT3011 → DMX1401AI, IT3011 → EE2211, MA1100T → YSC2209, MA1301 → MA1100, MA1301 → MA1100T, MA1301 → MA1311, MA1301 → MA1312, MA1301 → MA1505, MA1301 → MA1508E, MA1301 → MA1511, MA1301 → MA1512, MA1301 → MA1513, MA1301 → MA1521, MA1301 → MA1522, MA1301 → MA1531, MA1301 → MA2001, MA1301 → MA2002, MA1301 → MA2101, MA1301 → MA2101S, MA1301 → MA2104, MA1301 → MA2108, MA1301 → MA2108S, MA1301 → MA2116, MA1301 → MA2116T, MA1301 → MA2202, MA1301 → MA2202S, MA1301 → MA2213, MA1301 → MA2214, MA1301 → MA2288, MA1301 → MA2288R, MA1301 → MA2289, MA1301 → MA2289R, MA1301 → MA2301, MA1301 → MA2310, MA1301 → MA2311, MA1301 → MA2312U, MA1301 → MA2313, MA1301 → MA2401, MA1301 → MA3201, MA1301 → MA3205, MA1301 → MA3209, MA1301 → MA3210, MA1301 → MA3211, MA1301 → MA3211S, MA1301 → MA3220, MA1301 → MA3233, MA1301 → MA3236, MA1301 → MA3238, MA1301 → MA3238S, MA1301 → MA3252, MA1301 → MA3264, MA1301 → MA3265, MA1301 → MA3270, MA1301 → MA3288, MA1301 → MA3288R, MA1301 → MA3289, MA1301 → MA3310, MA1301 → MA3312, MA1301 → MA3313, MA1301 → MA4198, MA1301 → MA4203, MA1301 → MA4207, MA1301 → MA4211, MA1301 → MA4221, MA1301 → MA4229, MA1301 → MA4230, MA1301 → MA4233, MA1301 → MA4235, MA1301 → MA4251, MA1301 → MA4254, MA1301 → MA4255, MA1301 → MA4261, MA1301 → MA4262, MA1301 → MA4264, MA1301 → MA4266, MA1301 → MA4270, MA1301 → MA4273, MA1301 → MA4275, MA1301 → MA4276, MA1301 → MA4288O, MA1301 → MA4288P, MA1301 → MA4310, MA1301 → MA4312, MA1301 → MA4313, MA1301 → MA5198, MA1301 → MA5202, MA1301 → MA5204, MA1301 → MA5205, MA1301 → MA5206, MA1301 → MA5210, MA1301 → MA5213, MA1301 → MA5216, MA1301 → MA5217, MA1301 → MA5218, MA1301 → MA5219, MA1301 → MA5222, MA1301 → MA5232, MA1301 → MA5233, MA1301 → MA5243, MA1301 → MA5248, MA1301 → MA5249, MA1301 → MA5251, MA1301 → MA5252, MA1301 → MA5259, MA1301 → MA5260, MA1301 → MA5266, MA1301 → MA5270, MA1301 → MA5271, MA1301 → MA5272, MA1301 → MA5401, MA1301 → MA5402, MA1301 → MA6202, MA1301 → MA6211, MA1301 → MA6225, MA1301 → MA6291, MA1301X → MA1100, MA1301X → MA1100T, MA1301X → MA1311, MA1301X → MA1312, MA1301X → MA1505, MA1301X → MA1508E, MA1301X → MA1511, MA1301X → MA1512, MA1301X → MA1513, MA1301X → MA1521, MA1301X → MA1522, MA1301X → MA1531, MA1301X → MA2001, MA1301X → MA2002, MA1301X → MA2101, MA1301X → MA2101S, MA1301X → MA2104, MA1301X → MA2108, MA1301X → MA2108S, MA1301X → MA2116, MA1301X → MA2116T, MA1301X → MA2202, MA1301X → MA2202S, MA1301X → MA2213, MA1301X → MA2214, MA1301X → MA2288, MA1301X → MA2288R, MA1301X → MA2289, MA1301X → MA2289R, MA1301X → MA2301, MA1301X → MA2310, MA1301X → MA2311, MA1301X → MA2312U, MA1301X → MA2313, MA1301X → MA2401, MA1301X → MA3201, MA1301X → MA3205, MA1301X → MA3209, MA1301X → MA3210, MA1301X → MA3211, MA1301X → MA3211S, MA1301X → MA3220, MA1301X → MA3233, MA1301X → MA3236, MA1301X → MA3238, MA1301X → MA3238S, MA1301X → MA3252, MA1301X → MA3264, MA1301X → MA3265, MA1301X → MA3270, MA1301X → MA3288, MA1301X → MA3288R, MA1301X → MA3289, MA1301X → MA3310, MA1301X → MA3312, MA1301X → MA3313, MA1301X → MA4198, MA1301X → MA4203, MA1301X → MA4207, MA1301X → MA4211, MA1301X → MA4221, MA1301X → MA4229, MA1301X → MA4230, MA1301X → MA4233, MA1301X → MA4235, MA1301X → MA4251, MA1301X → MA4254, MA1301X → MA4255, MA1301X → MA4261, MA1301X → MA4262, MA1301X → MA4264, MA1301X → MA4266, MA1301X → MA4270, MA1301X → MA4273, MA1301X → MA4275, MA1301X → MA4276, MA1301X → MA4288O, MA1301X → MA4288P, MA1301X → MA4310, MA1301X → MA4312, MA1301X → MA4313, MA1301X → MA5198, MA1301X → MA5202, MA1301X → MA5204, MA1301X → MA5205, MA1301X → MA5206, MA1301X → MA5210, MA1301X → MA5213, MA1301X → MA5216, MA1301X → MA5217, MA1301X → MA5218, MA1301X → MA5219, MA1301X → MA5222, MA1301X → MA5232, MA1301X → MA5233, MA1301X → MA5243, MA1301X → MA5248, MA1301X → MA5249, MA1301X → MA5251, MA1301X → MA5252, MA1301X → MA5259, MA1301X → MA5260, MA1301X → MA5266, MA1301X → MA5270, MA1301X → MA5271, MA1301X → MA5272, MA1301X → MA5401, MA1301X → MA5402, MA1301X → MA6202, MA1301X → MA6211, MA1301X → MA6225, MA1301X → MA6291, MA1508E → MA1311, MA1511 → MA2002, MA1513 → MA1311, MA1522 → MA1311, MA1522 → YSC2232, MA1531 → MA1312, MA1531 → MA1505, MA1531 → MA1511, MA1531 → MA1521, MA1531 → MA2002, MA1531 → MA2104, MA1531 → YSC1216, MA2001 → YSC2232, MA2002 → YSC1216, MA2108S → YSC3206, MA2116 → YSC2243, MA2116T → EC2303, MA2116T → MA2301, MA2116T → YSC2243, MA2301 → MA1312, MA2301 → MA1505, MA2301 → MA1508E, MA2301 → MA1511, MA2301 → MA1513, MA2301 → MA1521, MA2301 → MA2001, MA2301 → MA2002, MA2311 → MA2108, MA2311 → MA2108S, MA3236 → DBA3701, MA3252 → DBA3701, ME2105 → ESP2111, ME2105 → ME2104, ME2105 → TME2143, ME2143E → ME2143, MNO2706 → IS2101, MNO2706 → IS3103, NM2207 → CS1010, NM2207 → CS1010A, NM2207 → CS1010E, NM2207 → CS1010HS, NM2207 → CS1010J, NM2207 → CS1010R, NM2207 → CS1010S, NM2207 → CS1010X, NM2207 → CS1101S, NM4259 → NM3221, NM4259HM → NM3221, PC1201 → PC1101, PC1432 → PC1432X, PC2174A → PC2134, RB2101 → EE1111B, RB2101 → ME2104, RB2101 → ME2105, SP1541 → ES2531, SP1541 → ES2631, SP1541 → ES2660, SP1541 → SP2271, SP1541 → UTW1001A, SP1541 → UTW1001AA, SP1541 → UTW1001C, SP1541 → UTW1001I, SP1541 → UTW1001J, SP1541 → UTW1001K, SP1541 → UTW1001P, SP1541 → UTW1001Q, SP1541 → UTW1001T, SP1541 → UTW1001V, SP1541 → UTW1001X, SP1541X → ES2531, SP1541X → ES2631, SP1541X → ES2660, SP1541X → SP2271, SP1541X → UTW1001A, SP1541X → UTW1001AA, SP1541X → UTW1001C, SP1541X → UTW1001I, SP1541X → UTW1001J, SP1541X → UTW1001K, SP1541X → UTW1001P, SP1541X → UTW1001Q, SP1541X → UTW1001T, SP1541X → UTW1001V, SP1541X → UTW1001X, ST1232 → CE2407, ST1232 → CN3421, ST1232 → ST1131, ST1232 → ST2334, ST2131 → CE2407, TEE4204 → CS2105, TEE4204 → CS3103, TEE4704 → CS4243, TEE4704 → EE4704E, UTC2851 → CS1010R, ZB2101 → LSM2241
