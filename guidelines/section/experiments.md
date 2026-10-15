# Experiments — guidelines 4편 분석

[skeleton.md](skeleton.md)의 하위 문서. §4 Experiments를 하위절(RQ) → 단락 단위로 분석한다.
본문의 약 40%를 차지하는 가장 긴 섹션이다. 표·그림의 **디자인**은 [floats.md](floats.md)에서 다루고, 여기서는 RQ 구성, 실험 설정, 결과를 **서술하는 문형**에 집중한다.
원문 발췌는 부록 A에 실었다.

---

## 0. 핵심 규칙

1. Experiments는 **~3,200 words, RQ 4–5개**다. 구성은 **리드(RQ 목록 + 구현·장비) → 4.1 Experimental Settings → RQ별 하위절 → (추가 분석) → Threats to Validity**다.
2. RQ 원형은 **① 주 지표(coverage) ② 부 지표(bugs) ③ 단계별 효과(ablation) ④ 일반성(다른 도구 계열)**이고, 여기에 하이퍼파라미터·분석·재사용성 중 하나를 더한다. **RQ 이름 = 하위절 제목**이다.
3. Settings는 **Baselines. / Benchmarks. / Other Settings.** bold run-in 세 단락이다. 벤치마크는 선행 연구에서 가져오고 **명시적 필터 기준**을 둔다. 예산·반복 횟수·장비·**공정성 장치**("we ran each baseline in two ways ... and reported the better")를 밝힌다.
4. 결과 단락은 **"Table N shows that ..." → 전체 평균 % → baseline별 수치(respectively) → Notably(최대) → Interestingly/Surprisingly(이상치 + 원인) → 통계 검정 + 표준편차 → "These results indicate ..."** 순이다.
5. Threats to Validity는 **한 단락, (1)(2)(3)**이다. 도구 일반성·벤치마크 대표성·하이퍼파라미터를 다루고, 항목마다 **완화 근거**를 붙인다. "may"가 집중적으로 나오는 유일한 곳이다.
6. **결과 문장의 ~75%는 장점(제안 기법의 우위 + baseline의 약점)이고, 단점은 ~13%다** (Threats 밖에서는 ~9%). 단점은 주 지표 하위절이 아니라 부차 분석과 Threats에 두고, 반드시 **양보절·축소어·원인 귀속** 중 하나와 함께 쓴다. Abstract·Intro·Conclusion에는 단점이 하나도 없다. 약해 보이는 결과는 **필요성·상보성·trade-off·확장성이라는 새 주장**으로 바꿔 쓴다 (§11–§13).

---

## 1. 분량

| ID | 하위절 (단어 수, 비율) | 합계 |
|---|---|---|
| ICSE25 | 리드 134 (5%) · A. Settings 409 (15%) · **B. Effectiveness 626 (23%)** · C. Each Stage 507 (18%) · D. Generality 215 (8%) · E. Hyperparameters 249 (9%) · F. Discussions 495 (18%) · G. Threats 111 (4%) | 2,746 |
| ICSE26 | 리드 103 (3%) · 4.1 Settings 352 (11%) · **4.2 Branch Coverage 758 (24%)** · 4.3 Bug-Finding 154 (5%) · 4.4 Two Stages 649 (21%) · 4.5 Self-configuration 660 (21%) · 4.6 Generality 322 (10%) · 4.7 Threats 108 (3%) | 3,106 |
| ASE26 | 리드 90 (3%) · 4.1 Settings 506 (15%) · **4.2 Branch Coverage 655 (19%)** · 4.3 Bug-finding 184 (5%) · **4.4 Stages 917 (27%)** · 4.5 Generality 307 (9%) · 4.6 Case Study 244 (7%) · 4.7 vs Fuzzing 306 (9%) · 4.8 Threats 174 (5%) | 3,383 |
| FSE26 | 리드 115 (3%) · 4.1 Settings 700 (20%) · **4.2 Effectiveness (crash + coverage) 1,374 (40%)** · 4.3 CE Ratio 252 (7%) · 4.4 Each Step 523 (15%) · 4.5 Reusability 354 (10%) · 4.6 Threats 146 (4%) | 3,464 |

역할 그룹별 평균 비중:

| 리드 | Settings | 주 결과 (coverage + bug) | Ablation | 추가 분석 (일반성·하이퍼파라미터·사례·비교) | Threats |
|---|---|---|---|---|---|
| ~4% | **~15%** | **~29%** | **~20%** | **~27%** | ~4% |

- 2단 논문은 단 단위로 다시 추출해 셌다. 하위절 경계에서 수십 단어 정도 오차가 있다.
- 주 결과와 ablation을 합치면 약 절반이다. 추가 분석(~27%)도 적지 않다. **RQ 목록에 없는 분석 하위절**도 둔다 (ICSE25 Discussions, ASE26 Case Study·Comparison with Fuzzing).
- 플로트: §4에 표 26개(전체의 81%)와 그림 10개가 있다. 논문당 표 4–9개, 그림 1–4개다.

---

## 2. 구조

### 2.1 하위절 유형

| 유형 | 내용 | 출현 |
|---|---|---|
| **E-0 리드** | "In this section, we evaluate X ... research questions:" + RQ 목록 + 구현·장비 1–2문장 | 4/4 |
| **E-1 Settings** | Baselines / Benchmarks / Other Settings | 4/4 (항상 4.1) |
| **E-2 주 지표** | coverage 결과 + 통계 | 4/4 |
| **E-3 부 지표** | 버그·크래시 결과 | 4/4 (독립 하위절 2편, 주 지표 안의 bold run-in 2편) |
| **E-4 Ablation** | 단계마다 변형과 비교 | 4/4 |
| **E-5 일반성** | 다른 도구 계열에 적용 (concolic testing) 또는 다른 프로그램에 재사용 | 4/4 |
| E-6 추가 분석 | 하이퍼파라미터, 파라미터 분석, 사례 연구, 외부 기법 비교, 연속 실행 비교 | 4/4 (형태는 다양) |
| **E-7 Threats** | (1)(2)(3) 한 단락 | 4/4 (항상 마지막 하위절) |

### 2.2 논문별 RQ와 하위절 대응

| ID | RQ (굵은 이름) | 하위절 | RQ 밖 하위절 |
|---|---|---|---|
| ICSE25 | 1) Effectiveness · 2) Efficacy of Each Stage · 3) Generality · 4) Impact of Hyperparameters | B · C · D · E | F. Discussions (연속 실행 비교, 좋은 seed의 특징, SMT 호출 절감) |
| ICSE26 | Branch coverage · Bug-finding ability · Efficacy of two stages · Analysis of self-configuration · Generality | 4.2 · 4.3 · 4.4 · 4.5 · 4.6 | — (4.2 안에 bold run-in 분석 2개) |
| ASE26 | (1) Branch Coverage · (2) Bug-finding Ability · (3) Effectiveness of Stages · (4) Generality | 4.2 · 4.3 · 4.4 · 4.5 | 4.6 Case Study, 4.7 Comparison with Fuzzing Techniques |
| FSE26 | (1) Effectiveness · (2) Reduction of coverage-equivalent inputs · (3) Efficacy of each step · (4) Reusability | 4.2 · 4.3 · 4.4 · 4.5 | — (4.2 안에 Case study 2개) |

**정형 순서:** 리드 → Settings → 주 지표 → 부 지표 → ablation → 일반성 → (추가 분석) → Threats. 순서가 바뀐 경우는 없다.

### 2.3 결과 하위절의 단락 역할

| 기호 | 역할 | 대표 표현 |
|---|---|---|
| **H** | 헤드라인 (표·그림 + 주장) | Table N shows / demonstrates that X significantly ... |
| **Q** | 수치 (전체 → baseline별) | Overall, ... X% more ... / ..., respectively |
| **N** | 두드러진 사례 | Notably, / Particularly, ... the largest ... |
| **S** | 이상치·의외 결과 + 원인 | Interestingly, / Surprisingly, ... The fundamental reason is ... |
| **T** | 통계 검정·변동 | statistically significant ... Mann-Whitney U test ... p < 0.05 / standard deviations ... |
| **D** | 심층 분석 (bold run-in) | **Comparison with ...** / **Case study.** |
| **C** | 함의 | These results indicate / demonstrate / highlight that ... |

**정형 순서:** H → Q → N → S → T → (D) → C.

---

## 3. 단위별 분석

### E-0 리드 — RQ 목록

| ID | 도입 문장 | RQ 형식 |
|---|---|---|
| ICSE25 | "In this section, we evaluate the effectiveness of TopSeed based on the following research questions:" | `1) **Effectiveness:** How effectively can ...?` (번호 목록) |
| ICSE26 | "We evaluate ParaSuit to answer the following research questions:" | `• **Branch coverage**: To what extent does ...?` (글머리표) |
| ASE26 | "In this section, we evaluate the efficiency of Orbis by addressing the following research questions:" | `(1) **Branch Coverage**: To what extent does ...?` |
| FSE26 | "In this section, we experimentally evaluate RSFuzz to answer the following four research questions:" | `(1) **Effectiveness**: How effectively does ...?` |

**RQ 문형** (17개 RQ 기준):

- "**How effectively** can / does X enhance ... in terms of A and B?" (4)
- "**To what extent** does X improve / reduce ...?" (3)
- "**How** does each stage of X **contribute to** performance improvement?" / "How significantly does each step ... contribute ...?" (ablation, 3)
- "**Is** X (generally) **applicable to** ...?" / "**Can** X **be applied to** ...?" (일반성, 3)
- "How do hyperparameter values affect ...?" / "Which parameters are most impactful? How do they ... vary by program?" / "Are the ... applicable to different programs ...?"
- ICSE26처럼 한 RQ에 질문 2–3개를 붙이기도 한다: "Does our parameter selection algorithm outperform naive approaches? Is our value sampling stage more effective than generic sampling methods?"

**RQ 이름**은 2–4단어 명사구다: Effectiveness / Branch Coverage / Bug-finding Ability / Efficacy of Each Stage / Generality / Reusability. **같은 이름을 하위절 제목으로 쓴다.**

**구현·장비 문장** (리드 끝 또는 Settings 끝):

- "We implemented TopSeed on top of KLEE-2.1 [4], an actively maintained symbolic executor that incorporates diverse techniques [11], [15], [17], [18], [26]. All experiments were conducted on a single Linux machine equipped with two Intel Xeon Gold 6230R processors."
- "We conducted our experiments using KLEE-2.1 [5], a widely used symbolic executor. All experiments were performed on a system with two Intel Xeon Gold 6230R processors and 256GB RAM."
- 틀: **"We implemented X on top of <도구-버전> [cite], <도구에 대한 한 구절>. All experiments were conducted on <장비>."**

### E-1 Experimental Settings

bold run-in 세 단락이 기본이다 (ICSE25·ASE26: **Baselines.** / **Benchmarks.** / **Other Settings.**, ICSE26: Baselines. / Other Settings., FSE26: 4.1.1 Baselines / 4.1.2 Benchmarks and Time Budgets).

#### Baselines

- **개수와 범주를 먼저** 밝힌다: "We compared the performance of four baselines integrated with TopSeed against their performance without TopSeed integration. The four baselines are: (1) base symbolic executor (KLEE [4]), (2) search strategy (Learch [11]), (3) state-pruning strategy (Homi [15]), and (4) constraint-solving strategy (KLEE-Array [18])."
- 각 baseline을 **한 문장으로 설명**한다: "Learch [11] is a novel learning-based search strategy that prioritizes states for exploration. Homi [15] is a cutting-edge state-pruning strategy that automatically eliminates redundant states while keeping promising ones."
- **비교 설정에 이름을 붙인다**: "the baseline without seeding (Base), the baseline with a random seed selection strategy (RandSeed), corresponding to Algorithm 2, and the baseline integrated with our approach (TopSeed), corresponding to Algorithm 3." / "(1) a pure implementation without modifications, as publicly available (Pure), and (2) an integration of Orbis with each technique (Orbis)."
- **baseline 구성 원형:**
  - SOTA ("the state-of-the-art approach ... It requires 20 user-configured parameter spaces")
  - SOTA의 변형 (Symtuner_AllP: 모든 파라미터를 쓰도록 바꾼 SymTuner)
  - **제안 기법의 단순판** (RandSeed, RandSuit: "a naive version of ParaSuit that randomly selects ...") — §2의 단순 대안이 여기서 baseline이 된다
  - 기본 도구 그대로 (KLEE, Kleefix)
- **강한 baseline임을 강조**한다: "Given that Symtuner is an arguably strong baseline, this choice ensures a rigorous evaluation for ParaSuit." / "Each enhances symbolic execution through an independent approach and has shown superior performance over its own baselines."
- **baseline 설정의 근거**를 밝힌다: "we set k to 5, the best-performing value reported in Tribble's evaluation" / "The probabilistic fuzzer was executed with both PCFGs, and the best result was reported as ProbF."

#### Benchmarks

- **출처 = baseline들이 쓴 벤치마크의 합집합**: "we initially collected all available programs used in the experiments by the four baselines [4], [11], [15], [18]."
- **필터 기준 (1)(2)를 예시와 함께**:
  - "(1) we filtered out smaller programs with fewer than 1,000 total branches, as the baselines achieved high code coverage for these programs even without seeding (e.g., tty-8.31). (2) we also omitted programs (e.g., objcopy-2.36) where all baselines managed to cover less than 2.0% of total branches over 10 hours, indicating that the baselines failed to test the core functionality ..."
  - "First, we chose JavaScript, JSON, CSV and Markdown, which are the most commonly used input formats in previous works on fuzzing [..]. Second, among benchmarks using these formats, we included only those used at least twice in prior work."
- **다양성·대표성을 수치로**: "the number of options in our 15 benchmarks ranges from 15 to 158 (10×), and the number of option-related branches ranges from 30 to 8,080 (269×), ensuring a diverse and representative benchmark set." / "most benchmarks (8 out of 12) are not standalone parsers but non-trivial functionality beyond parsing."
- **선행 연구에서 쓰였음**: "these benchmarks have also been widely used in existing works [12, 13, 18, 44, 54, 80]"
- 끝에 벤치마크 표를 참조한다: "Table 2 presents the 15 open-source C programs used in our evaluation, along with the number of options in each program (Opt), ..."

#### Other Settings

| 항목 | 예 |
|---|---|
| 예산 | "we allocated a total testing budget of 10 hours per benchmark program" / 24 hours |
| 반복 | "Each experiment was conducted five times, and the average results were reported." (4/4, 5회) |
| **공정성 장치** | "to ensure a fair comparison, we ran each baseline without seeding (Base) in two ways: (1) by running it once for the total testing budget (10 hours) without termination, or (2) by running it multiple times within a shorter budget (120 seconds), similar to TopSeed (Algorithm 3). The better result between the two approaches was reported as Base." (ICSE25·ICSE26·ASE26) / "We also configured all baselines to potentially generate the same command-line arguments as Orbis." |
| 규모 강조 | "generating the coverage results reported in Table 3 required 18,000 hours when using a single CPU core (i.e., 24 hours × 5 trials × 15 benchmarks × 5 baselines, each tested with and without Orbis)" / "which exceeds the durations used in evaluations with three baseline fuzzers" |
| 측정 도구 | "We obtained branch coverage results using gcov [19], a widely used code coverage measurement tool." / jacoco [40] |
| 지표 정의 | "We evaluated the effectiveness of our approach using two metrics: option-related branch coverage, which Orbis primarily targets, and total branch coverage, a main objective of symbolic execution techniques." |

### E-2 주 지표 (coverage)

단락 순서 H → Q → N → S → T → (D) → C를 그대로 따른다.

- **H + Q:** "**Table V shows that** integrating TopSeed into each of the four baselines **significantly increased** branch coverage across all benchmarks, compared to the baselines without TopSeed. **Overall**, TopSeed covered 33.0% more branches than KLEE+Base, ... integrating TopSeed with Learch, Homi, and KLEE-Array, resulted in 38.1%, 31.6%, 40.1% increases in branch coverage, **respectively**, over each baseline without seeding."
- **N (부분집합·최대):** "**Particularly**, TopSeed dramatically increased branch coverage achieved by four baselines on large benchmarks, which have a greater potential for improvement than smaller ones. For the five largest programs, ... **Conversely**, on the five smallest programs, the improvements were modest, ..." / "**For instance**, in the case of the largest program xorriso, ParaSuit achieved 106.6% higher branch coverage than Symtuner, the second-best baseline—making the largest difference across all benchmarks."
- **S (이상치 + 함의):** "**Surprisingly**, for the dd program, Learch+RandSeed covered 63.2% fewer branches than Learch+Base. **This inconsistency of RandSeed underscores the necessity of our approach** (Algorithm 3) to achieve stable and high coverage across various benchmark programs." / "**Interestingly**, in grep, Symtuner even covered 2% fewer branches than RandSuit ... **This finding highlights a key limitation of** Symtuner—its use of a predefined configuration regardless of the target program."
  - 이상치는 **baseline의 약점**을 드러내는 쪽으로 해석한다.
- **T (통계):**
  - "**These results in Table V were statistically significant**: on 16 of the benchmark programs, the p value between Base and TopSeed across the four baselines was less than 0.05 according to the **Wilcoxon signed-rank test**. **An exception occurs** in the factor program, where ..."
  - "The coverage results of ParaSuit are statistically significant. This is confirmed by the **Mann-Whitney U test** [63], with p-values below 0.05 in all 48 cases (12 benchmarks × 4 baselines)."
  - 표준편차는 본문에 괄호로 쓴다: "The standard deviations of branch coverage ... were as follows: Base (38.6), RandSeed (73.1), and TopSeed (52.0). **As expected**, RandSeed showed the highest variability. **While** the standard deviation of TopSeed was slightly higher than Base, **this difference was negligible** given ..."
  - 검정: Wilcoxon signed-rank (1편), Mann-Whitney U (3편). 4편 모두 p < 0.05를 기준으로 하고, **예외를 숨기지 않는다**.
- **D (심층 분석, bold run-in):**
  - ICSE26: "**Comparison with User-configured Approach.** To demonstrate how ParaSuit achieved higher branch coverage than the state-of-the-art approach (Symtuner), we analyzed the differences in selected parameters and values. Figure 3-(a) shows that ..."
  - ICSE26: "**Comparison with 24-Hour Continuous Run.** To examine whether ParaSuit's iterative approach ... limits its ability to explore deeper paths, we compared it with Klee24h ..."
  - ASE26: OB coverage와 전체 coverage의 상관 (Pearson 0.902) — §2에서 미리 인용한 근거를 여기서 제시한다.
  - FSE26: "**Case study.** We conducted a detailed case study to investigate how ..."
- **C (함의):** "These results show that Orbis is complementary to existing symbolic execution techniques despite their different underlying methodologies." / "These results indicate that ParaSuit effectively tailors parameter selection to each program's unique characteristics."

### E-3 부 지표 (bugs / crashes)

- **집계 방법을 먼저 밝힌다** (4/4):
  - "To gather these bug-finding results, we first generated inputs by running each baseline in three modes ... We then selected inputs flagged as bugs by each baseline. Finally, we verified and extracted reproducible bug-triggering inputs by executing the original binary of each program with these selected inputs."
  - "A bug-triggering test-case was considered unique if its error location reported by KLEE differed from others."
  - "Table 4 reports the number of crashes with distinct stack traces detected by each fuzzer, **following previous works** [..]" / "We deliberately filtered out syntax-related errors (e.g., InvalidSyntax), as these are typically considered less critical than semantic errors [24]."
- **결과 문형:**
  - 합계: "In total, ParaSuit succeeded in detecting 11 unique bugs across three of the 12 programs ... This count is 4 more than the state-of-the-art Symtuner"
  - **놓친 것이 없음**: "Notably, ParaSuit did not miss any bugs that other baselines detected, while it successfully identified four additional bugs." / "Orbis not only preserved all bugs detected by the pure techniques but also uncovered additional ones." / "while missing only two"
  - 독점 발견: "exclusively detected", "missed by ... but also by the random seed selection strategy"
- **개발자 확인** (4/4): "the bug in gawk was confirmed by the original developers" / "All bugs discovered by ParaSuit were reported to the program developers" / "we reported these reproducible crashes to the corresponding developers and have received confirmation that one bug ... has been fixed"
- 분량이 적다 (150–250 words). 독립 하위절이 아니면 주 지표 하위절 안의 bold run-in(**Bug-Finding Capability.**, 4.2.1)으로 둔다.

### E-4 Ablation (단계별 효과)

- **리드 = 변형 정의:** "We evaluated the effectiveness of the Select and Learn stages in TopSeed (Algorithm 3). Specifically, for the Select phase, we assessed TopSeed's performance without the grouping and clustering algorithms ... In this variant, **dubbed** 'TopSeed without grouping', each input ... is treated as a separate group."
- **변형 유형:**

| 유형 | 예 | 정의 문형 |
|---|---|---|
| 제거 | TopSeed − (Group), Orbis-Extract, RSFuzz without the Select step | "a variant that omits this stage" / "does not select ... but instead uses all groups" |
| 무작위 대체 | RandP, RandV, RandConst, RandGuide | "randomly selects parameters to be tuned from all available parameters extracted by the Initialize function (line 4 in Algorithm 1)" |
| 전부·하나 | AllP, CallAll, AllConst, OneConst | "selects all available parameters, proceeding directly to the value sampling stage without any filtering" |
| SOTA 부품 대체 | SymP, SymV, FuzzConst (ZigZagFuzz), CitConst (HSCA), Bayesian·Genetic·CMA-ES, ParamILS·OpenTuner | "replaces the Construct function with the option-argument construction mechanism of ZigZagFuzz [26], a state-of-the-art program-option fuzzer" |

- **변형은 알고리즘 줄 번호로 정의**한다: "(the Sample procedure at line 20 of Algorithm 1)", "replaced the set ArgD constructed at line 4 in Algorithm 2 with the following ArgD′:"
- **공정성:** "To ensure fair comparisons, we set each parameter's sampling range to the interval [lv, hv], spanning the smallest to largest values sampled by ParaSuit ..." / "Since both ZigZagFuzz and HSCA are publicly available, we used their original implementations without modification."
- **결과:** "Results in Table VII **confirm the critical roles of** both Select and Learn stages ..." / "Table 4 demonstrates that our parameter selection algorithm **surpasses** the three simpler selection approaches." / "The results in Table 6 confirm that both the Select and Capture steps in RSFuzz **play a crucial role** in its performance."
- **단계 간 비교:** "Although both ... are essential, the grouping algorithm **has a more pronounced impact**." / "We also observed that the relative importance of the Select and Capture steps varied across benchmarks and fuzzers."
- **왜 이겼는지 설명:** "**We investigated why** Orbis notably outperformed CitConst. **The key difference is their objective.** ... In contrast, Orbis continuously evaluates ..."
- **변형이 baseline보다도 나쁜 경우를 짚는다:** "The most naive variant, which lacks both steps, ... performing even worse than the baseline fuzzers alone."
- **마무리:** "These findings demonstrate that both the Select and Capture steps are essential for the effectiveness of RSFuzz."
- 벤치마크: 전체(ASE26, FSE26) 또는 큰 프로그램 5개(ICSE25, ICSE26 — "covering the three largest programs ... and the three programs where bugs were identified").

### E-5 일반성 (Generality / Reusability)

- **SE 세 편은 같은 실험이다**: concolic testing 도구(CREST [..])와 그 위의 SOTA(Chameleon [..])에 적용하고, **Chameleon 논문의 벤치마크**(가장 큰 3–4개)를 같은 예산으로 쓴다.
  - "We examined if our seeding approach is applicable to concolic testing [1], [3], a major variant of symbolic execution. We integrated TopSeed with CREST [28], a popular concolic testing tool ..."
  - **이식 방법을 밝힌다**: "Integrating Orbis into a concolic testing engine corresponds to replacing the Execute procedure (Algorithm 1) with a concolic testing procedure [4, 9]. The main difference is ... To address this, we modified ..."
  - 결과: "On average, TopSeed increased branch coverage by 7.8% compared to CREST and 3.9% compared to Chameleon. **Interestingly**, with the seeding provided by TopSeed, the basic concolic testing tool CREST occasionally outperformed the advanced, unseeded Chameleon ..."
  - 함의: "These results indicate that TopSeed is versatile and can be generalized to other symbolic execution tools ..."
  - 실험 없이 **이식 가능성 논증**을 덧붙이기도 한다: "We also found that integrating ParaSuit with other symbolic execution tools: angr [77] and SPF [68], requires only minor modifications. ... we believe that integration with these tools is straightforward."
- **FSE26은 재사용성**: 한 프로그램에서 얻은 결과를 같은 입력 포맷의 다른 프로그램에 적용한다. 장단점을 함께 쓴다: "**Unquestionably**, RSFuzz achieves the best results when it generates recurrent sequences from a specific program ... **However, if the goal is to reduce the overhead** ..., reusing sequences ... is a practical and effective alternative."

### E-6 추가 분석

| 유형 | 예 | 문형 |
|---|---|---|
| 하이퍼파라미터 | ICSE25 E | "We assessed the impact of varying three hyperparameters—η_time, η_Learn, and η_r—on the effectiveness of TopSeed. Our approach (Algorithm 3) sets these default values to 120, 20, and 0.75, respectively. The first parameter, η_time, dictates ... On the five largest benchmarks, we calculated ... using various values around the default settings." → "Table IX demonstrates that the default hyperparameter values generally achieved the most stable and high branch coverage ..." |
| 연속 실행 비교 | ICSE25 F, ICSE26 4.2 | 짧은 실행을 반복하는 설계가 깊은 탐색을 해치지 않는지: "Results indicate that TopSeed covers, on average, 95% of the branches reached during continuous 10-hour symbolic executions" (Venn) |
| 내부 동작 분석 | ICSE26 4.5 | "**Impact of Selected Parameters.** ... we measured the first-order Sobol indices [79] ..." / "**Tendency of Selections and Sampled Values.**" / "**Efficiency of Self-configured Parameter Sets.**" |
| 사례 연구 | ICSE25 F, ASE26 4.6, FSE26 4.2 | "**To illustrate how** Orbis guides symbolic execution to achieve higher total branch coverage, **we conducted a case study on** the diff program." → 코드 조각 → 메커니즘 → **수치 대비** ("in just 7.1 seconds ... 9,012.7 seconds—approximately 1,269× longer", "the probability of generating this exact sequence is approximately 1 in 4,000,000") |
| 외부 계열 비교 | ASE26 4.7 | 다른 계열(fuzzer)과 비교. **공정성 조건을 길게 쓴다**: "unlike Orbis, which operates fully automatically, these fuzzers require manual intervention ... For a fair comparison, we provided the fuzzers with all information obtained from the Extract stage ..." 그리고 상대가 이긴 부분도 인정한다: "In contrast, these fuzzers exclusively covered 20,193, 6,505, and 6,211 branches, primarily because ..." |
| 메커니즘 지표 | ICSE25 F (SMT 호출 절감), FSE26 4.3 (CE 비율) | 향상의 **원인**이 되는 내부 지표를 따로 측정한다 |

- 사례 연구는 **향상이 가장 컸던 프로그램**을 고른다: "we conducted a case study on the diff program, which showed the highest improvement in terms of branch coverage."

### E-7 Threats to Validity

| ID | 항목 |
|---|---|
| ICSE25 | (1) KLEE·CREST에서만 평가 → 다른 도구에서 다를 수 있음 (2) 하이퍼파라미터를 trial and error로 정함 → "Although Section IV-E demonstrates stable performance ..., these settings may not be optimal ..." (3) 17개 벤치마크 → "While this benchmark suite includes all major programs used in the four baselines, it may not sufficiently evaluate ..." |
| ICSE26 | (1) 하이퍼파라미터 2개 → 같은 방법으로 자동 조정, "only a 1% drop when η_clust is set to 0.9" (2) 12개 C 프로그램 → "may not be representative of all types of programs" |
| ASE26 | (1) help 출력에서만 옵션 추출 → "our manual inspection shows that fewer than one hidden option exists per benchmark program on average (0.7 per program) ... improving branch coverage by only about 1%" (2) 간접 제어 의존성 미고려 → "incorporating more precise control-dependence analysis could further improve performance" (3) KLEE·CREST → 다른 엔진 [12, 21] |
| FSE26 | (1) **Benchmarks**: 12개, 대표성 (2) **Generality**: 더 정교한 fuzzer [..]에서는 다를 수 있음 (3) **Other grammars**: 다른 CFG(XML, CSS)에도 적용될 것으로 기대하지만 보장할 수 없음 |

- 형식: **한 단락, 인라인 (1)(2)(3)** (FSE26은 "(1) Benchmarks:"처럼 이름표를 붙인다). 100–175 words.
- 항목 구성: **사실(우리가 한 것) → 한계("may not ...") → 완화 근거(다른 절의 결과, 수동 조사 수치)**
- 범주: 도구·엔진 일반성 (4/4), 벤치마크 대표성 (3/4), 하이퍼파라미터 (2/4), 방법 자체의 가정 (ASE26 2개, FSE26 1개)
- 완화 근거는 **다른 하위절을 다시 인용**하거나 **수치**로 댄다.

---

## 4. 문체 특징

| 항목 | 관찰 |
|---|---|
| 주어 | **표·그림**(Table N shows ...), **도구 조합**(KLEE+TopSeed, ProbF+RSFuzz), **we**(we evaluated, we observed, we investigated) |
| 시제 | 수행·관찰은 **과거형**(covered, identified, achieved, observed), 표가 보여 주는 것은 **현재형**(Table 2 demonstrates), 함의는 **현재형**(These results indicate) |
| 결론 문장 | "These results / This finding indicate·demonstrate·highlight·underscore·confirm that ..." — 논문당 3–6회, "This indicates/suggests ..." 0–4회 |
| 신호어 (논문당 빈도) | Notably, (0–5) / Interestingly, (0–3) / Surprisingly, (0–2) / Particularly·In particular, (0–3) / Overall·On average, (1–4) / respectively (3–13) |
| 수치 | % 소수 1자리, 큰 배율은 ×("3.5 times", "66.9×"), baseline 나열은 "respectively", 표준편차는 괄호 |
| 통계 | "statistically significant"를 논문마다 정확히 한 번 쓴다. 검정 이름 + 인용 + 기준 p < 0.05 + 예외 |
| 공정성 | "To ensure a fair comparison," / "For a clear comparison," / "without modification" — 4/4 |
| hedging | 결과 서술에는 거의 없다. "may / might"는 논문당 2–3회이고 대부분 Threats와 원인 추정("This might stem from")에 있다 |
| 강조 형용사 | significantly, substantially, dramatically, remarkably, markedly, considerably, noticeably |
| 정직성 | 예외·상대가 이긴 부분·약점을 **일부** 쓴다 ("An exception occurs ...", "while missing only one bug", "these fuzzers exclusively covered ...", "Despite the negative side effect, ..."). 단, 표에 이미 보이거나 리뷰어가 물을 만한 것만 골라 쓰고, 쓸 때는 반드시 축소·상쇄 장치를 붙인다 → §11–§12 |
| **넣지 않는 것** | 방법 재설명 (§3 참조로 대체), Related Work식 문헌 비교 |

---

## 5. 수식·알고리즘·플로트

> 캡션·선·강조·색 같은 디자인은 [floats.md](floats.md) §2–§4를 따른다. 여기서는 하위절마다 **어떤 플로트를 두는지**만 정리한다.

| 하위절 | 플로트 | 예 |
|---|---|---|
| Settings | **벤치마크 표** (2–3단으로 접음) | ICSE25 IV, ICSE26 1, ASE26 2, FSE26 3 |
| 주 지표 | **주 결과표** (벤치마크 × 도구 × 설정, Total 행), 필요하면 분석 그림 | ICSE25 V, ICSE26 2 + Fig. 3, ASE26 3·4, FSE26 5 |
| 부 지표 | **버그 표** (버그가 나온 벤치마크만) | ICSE25 VI, ICSE26 3, ASE26 5, FSE26 4 |
| Ablation | **ablation 표** 1–4개 | ICSE25 VII, ICSE26 4·5, ASE26 6–9, FSE26 6 |
| 일반성 | 작은 표 또는 **Venn 그림** | ICSE25 VIII, ICSE26 Fig. 6, ASE26 Fig. 3, FSE26 Fig. 4 |
| 하이퍼파라미터 | 파라미터 그룹 표 | ICSE25 IX |
| 분석·사례 | 막대·선·범위 그래프, **Venn**(연속 실행 비교), **코드 조각** | ICSE25 Fig. 2–4·X, ICSE26 Table 6·Fig. 4–5, ASE26 사례 코드·Table 10 |

- **수식은 거의 없다** (ASE26 ablation 변형 정의 1개). 변형은 알고리즘 줄 번호로 정의한다.
- **RQ마다 플로트가 최소 1개** 있고, 결과 단락의 첫 문장이 그 플로트를 주어로 삼는다.

---

## 6. 섹션 간 연결

| §4 요소 | 대응 위치 | 관계 |
|---|---|---|
| RQ 목록 | Intro I7 (결과 미리보기), Contributions bullet 3 | Intro의 "We further demonstrate X's efficacy by comparing it with ..., and its generality by applying ..." 문장이 RQ와 일대일로 대응한다 |
| 주 지표 수치 | Abstract M8, Intro I7 | 같은 수치를 쓴다 (반올림 규칙까지 일치시킬 것; [floats.md](floats.md) §7) |
| Baselines | §2.1 SOTA 대응, §2.2 단순 대안, §5 Related Work | 같은 기법이 §2 → §4 → §5에 다시 나온다. §2의 단순 대안이 baseline이 된다 (ICSE25 Algorithm 2 → RandSeed) |
| Benchmarks | §2.2 Table 1 (일부), Intro I7 (개수·규모 범위) | §2.2의 측정은 이 벤치마크의 일부로 한다 |
| Ablation 변형 | §3 단계, §3 forward ref, §3 "we also considered" | §3에서 "as demonstrated in Section 4.4"로 미리 인용한 수치가 여기서 나온다 (ASE26 9.6%, 21.5%, 16.8%) |
| 일반성 | §2.1 Algorithm 1 | 다른 도구로 옮길 때 Algorithm 1(Execute)만 바꾼다 |
| 하이퍼파라미터 | §3 η "by trial and error", Threats | 민감도 분석 → Threats에서 "Although Section IV-E demonstrates ..."로 다시 인용 |
| Threats 완화 근거 | §3 "We acknowledge ..." | ASE26: §3의 hidden options 0.9%와 Threats의 0.7개/프로그램은 표현 단위가 다르다 |
| 사례 연구 | §2 예제 프로그램, §3 메커니즘 | §2·§3의 예제 프로그램(diff, ls)으로 메커니즘을 실측한다 |

---

## 7. 템플릿

```text
## 4 Experiments
In this section, we evaluate <Tool> to answer the following research questions:
  (1) Effectiveness: How effectively does <Tool> improve <metric1> and <metric2> compared to <baselines>?
  (2) Efficacy of Each Stage: How does each stage of <Tool> contribute to its performance?
  (3) Generality: Is <Tool> applicable to <another tool family / setting>?
  (4) <Extra>: <hyperparameters / reusability / analysis question>?
We implemented <Tool> on top of <tool-version> [..], <one-phrase description>. All experiments were conducted on <machine>.

### 4.1 Experimental Settings
Baselines. We compared <Tool> with <N> baselines: (1) <category> (<Name> [..]), (2) .... <Name> [..] is <one-sentence description>.
  We evaluated each baseline in <K> settings: <Base>, <naive variant (Algorithm 2)>, and <Tool>.
Benchmarks. We used <N> <subjects> in Table N. To construct our benchmark suite, we collected all <subjects> used by <baselines> [..].
  We then selected <N> based on two criteria: (1) ... (e.g., <excluded>), and (2) ... (e.g., <excluded>).
Other Settings. We allocated <budget> per <subject>. Each experiment was repeated five times, and we report the average.
  To ensure a fair comparison, we ran each baseline in two ways ... and reported the better result. We measured <metric> using <tool> [..].

### 4.2 <Metric1>
Table N shows that <Tool> significantly improved <metric> across all <subjects>. Overall, <Tool> achieved X% higher <metric> than <SOTA>,
  and A%, B%, and C% higher than <b1>, <b2>, and <b3>, respectively.
Notably, on <largest subject>, .... Interestingly, <baseline> even <worse than naive>. This finding highlights a key limitation of <baseline>: ....
These results were statistically significant: the Mann-Whitney U test [..] yielded p-values below 0.05 in <k> of <n> cases. The standard deviations were ... (...).
These results indicate that ....

### 4.3 <Metric2: bugs>
To obtain these results, we collected ..., re-executed ..., and retained only reproducible .... A bug was considered unique if ....
In total, <Tool> detected <N> unique bugs, <k> more than <SOTA>. Notably, <Tool> did not miss any bug detected by other baselines.
All bugs were reported to the developers, and <k> were confirmed.

### 4.4 Efficacy of Each Stage
We compared <Tool> with <k> variants: <Tool>-<Stage>, which omits ...; Rand<Stage>, which replaces <F> (line N of Algorithm M) with ....
Table N confirms the critical role of each stage: <Tool> achieved X%, Y% higher <metric> than .... We investigated why ...: the key difference is ....
These findings demonstrate that both <A> and <B> are essential for the effectiveness of <Tool>.

### 4.5 Generality
We examined whether <Tool> is applicable to <family>. Integrating <Tool> into <engine> corresponds to replacing the Execute procedure (Algorithm 1) ....
On average, <Tool> increased <metric> by X% for <e1> and Y% for <e2>. These results demonstrate the generality of <Tool>.

### 4.6 Threats to Validity
(1) We evaluated <Tool> on <engines>; its performance may vary on other engines. (2) <hyperparameters> were determined by trial and error.
Although Section 4.x shows stable performance ..., these settings may not be optimal for .... (3) Our <N> benchmarks ... may not be representative.
```

---

## 8. 작성 체크리스트

- [ ] 리드에 RQ 4–5개를 "**Name**: question?" 형식으로 두고, RQ 이름과 하위절 제목이 같은가
- [ ] RQ에 주 지표·부 지표·ablation·일반성이 모두 있는가
- [ ] 구현 기반(도구-버전)과 장비를 한두 문장으로 밝혔는가
- [ ] Baselines에 범주·한 줄 설명·인용이 있고, 제안 기법의 단순판(§2 단순 대안)이 baseline에 들어갔는가
- [ ] Benchmarks가 선행 연구의 합집합에서 출발하고, 필터 기준 (1)(2)와 제외 예시가 있는가
- [ ] 예산, 5회 반복 평균, 공정성 장치, 측정 도구를 밝혔는가
- [ ] 결과 단락이 H → Q → N → S → T → C 순이고, 첫 문장이 표·그림을 주어로 하는가
- [ ] 이상치를 숨기지 않고 원인과 함의(대개 baseline의 약점)를 썼는가
- [ ] 통계 검정 이름·인용·p 기준·예외, 표준편차를 썼는가
- [ ] 버그 집계 방법(재현, 고유성 기준)과 개발자 보고·확인을 썼는가
- [ ] ablation 변형을 알고리즘 줄 번호로 정의하고, 왜 이겼는지 설명했는가
- [ ] 일반성 실험에서 이식 방법(Algorithm 1의 어디를 바꿨는지)을 밝혔는가
- [ ] 사례 연구가 향상이 가장 큰 대상을 골라 구체적 수치 대비로 끝나는가
- [ ] Threats가 (1)(2)(3) 한 단락이고, 항목마다 완화 근거가 있는가
- [ ] 본문 수치·표·Abstract·Intro가 모두 같은 산출물에서 나왔는가 ([floats.md](floats.md) §7)

---

**결과 보고의 수사 (§9–§14)**

§0–§8이 **무엇을 어떤 순서로** 쓰는지를 다뤘다면, §9–§14는 **결과를 어떻게 보이게 하는지**를 다룬다.

- **방법.** 4편의 §4 전체, Abstract, Intro의 결과·기여 단락, §3의 한계 언급, Conclusion을 읽었다. 결과를 보고하거나 해석하는 문장을 모두 하나씩 코딩했다 (setup 문장은 제외). 표와 그림은 렌더링한 PDF로 셀 단위까지 대조했고, 본문 인용은 원문 텍스트에서 다시 검색해 확인했다.
- **코딩 기준.**
  - **F**: 제안 기법에 유리한 결과.
  - **U**: 제안 기법의 약점. 지거나 비기거나, 벤치마크마다 달라지거나, 비용이 더 들거나, 실패하거나, 한계가 있는 경우.
  - **B**: baseline의 약점을 제안 기법의 근거로 쓴 문장.
  - **N**: 중립.
  - 장점과 약점이 섞인 문장은 약점이 들어 있으면 U로 셌다.
- **오차.** 논문마다 같은 기준으로 따로 코딩했으므로 경계 사례에서 ±2–3문장의 오차가 있다.

---

## 9. 플로트: 무엇을 표로, 무엇을 그림으로

### 9.1 §4의 플로트 개수

| ID | 결과 표 | 설정 표 | 결과 그림 | 코드 | 텍스트로만 보고한 실험 |
|---|---|---|---|---|---|
| ICSE25 | 6 (V–X) | 1 (IV) | 2 (Fig. 2 선, Fig. 3 Venn ×5) | 1 (Fig. 4) | 연속 실행 수치 일부 |
| ICSE26 | 5 (2–6) | 1 (1) | 4 (Fig. 3 막대+범위, 4 정렬 막대, 5 범위, 6 Venn ×4) | — | **6개** (Klee24h, prior-knowledge, ParamILS·OpenTuner, Kleenew, SD·MWU, η_clust) |
| ASE26 | 8 (3–10) | 1 (2) | 1 (Fig. 3 Venn ×8) | 1 (번호 없는 listing) | AllConst·OneConst, Pearson, CitConst 진단, Guide 오버헤드 |
| FSE26 | 3 (4–6) | 1 (3) | 2 (Fig. 3 묶음 막대, Fig. 4 가로 막대) | — | ReG ablation, identifier 사례, SD |
| **합계** | **22** | **4** | **9** | **2** (번호 있는 그림 1 + listing 1) | |

- **결과 플로트의 71%(22/31)가 표다.** 그림이 표보다 많은 논문은 없다 (ICSE26이 5:4로 가장 가깝다).
- **RQ마다 플로트가 1–4개다.** 주 지표 RQ는 표 1–2개, ablation RQ는 표 1–4개다 (ASE26은 단계마다 표 1개씩 4개). 일반성 RQ는 표나 그림 1개다.

### 9.2 결과 유형별 선택

| 결과 유형 | 형식 | 출현 | 예 |
|---|---|---|---|
| **baseline과의 정면 비교** (벤치마크 × 도구 × 설정) | **항상 표** + Total 행 | 4/4, 예외 없음 | ICSE25 V, ICSE26 2, ASE26 3·4, FSE26 5 |
| 버그·크래시 수 | 표 (버그가 나온 벤치마크만) | 4/4 | ICSE25 VI, ICSE26 3, ASE26 5, FSE26 4 |
| ablation | 표. 변형을 열에 두고 셀은 "커버리지(버그)" | 4/4 | ICSE25 VII, ICSE26 4·5, ASE26 6–9, FSE26 6 |
| 하이퍼파라미터 3점 sweep | 표 (선 그래프가 아님) | 1/4 | ICSE25 IX |
| **겹침·고유성** | 사례가 8개 이하면 **Venn**, 많으면 표 | 3/4 | Venn: ICSE25 Fig. 3, ICSE26 Fig. 6, ASE26 Fig. 3 / 표: ASE26 Table 10 (45개), FSE26 Table 4 (차집합 열) |
| 시간에 따른 추이 | 선 그래프 | **1/4** (그것도 학습 가중치이고, coverage-over-time은 0/4) | ICSE25 Fig. 2 |
| 구성·빈도·범위 (방법이 **어떻게** 동작하는지) | 막대·범위 그래프 | 1/4 | ICSE26 Fig. 3–5 |
| 비율 지표 하나의 패턴 | 묶음 막대 | 1/4 | FSE26 Fig. 3 (coverage-equivalent %) |
| 2×2 재사용 설계 | 가로 막대 (**x축을 잘라** 차이를 크게 보이게 함) | 1/4 | FSE26 Fig. 4 |
| 사례 연구 | 코드 조각 | 2/4 | ICSE25 Fig. 4, ASE26 listing |

**규칙:**

1. **비교는 표, 설명은 그림이다.** 정확한 수치로 "이겼다"를 보여야 하는 결과는 모두 표다. 그림은 겹침(Venn), 메커니즘(가중치 추이, 파라미터 분포), 사례(코드)에 쓴다.
2. **표가 그림보다 결과를 더 많이 감춘다.** 표는 숫자의 격자라 독자가 직접 찾지 않으면 지는 셀이 눈에 띄지 않는다. 같은 데이터를 그림으로 그리면 바로 보인다. 겹침이 45개인 ASE26 Table 10에서 ZigZagFuzz가 9/15 프로그램에서 더 많은 고유 분기를 덮었다는 사실은 표 안에만 있다.
3. **그림 4편 어디에도 없는 것:**
   - coverage-over-time 곡선 (10–24시간 실행인데도)
   - 분산을 보여 주는 box plot이나 신뢰구간
   - **제안 기법 자체의 비용·오버헤드 플로트**

   평균만 보여 주면 변동과 오버헤드를 보일 자리가 없다.
4. **부차 실험은 텍스트로만 보고한다.** ICSE26은 실험 6개를 플로트 없이 수치 1–2개로만 썼다. 텍스트로만 보고하면 벤치마크별 세부(지는 프로그램)가 드러나지 않는다.

---

## 10. 실험 규모

| | ICSE25 | ICSE26 | ASE26 | FSE26 |
|---|---|---|---|---|
| 벤치마크 | 17 C 프로그램 (8K–251K LoC) | 12 GNU 프로그램 (5K–161K LoC) | 15 C 프로그램 (분기 3.8K–48.7K) | 12 프로그램, 4 포맷 (1.5K–77.4K LoC) |
| 벤치마크 출처 | baseline 4개 논문의 합집합 + 필터 | Symtuner 논문 그대로 | baseline 논문 + 필터 | 선행 연구에서 2회 이상 쓰인 것 |
| 비교 구성 | baseline 4 × 설정 3 = 12 (+ Base 2방식) | 주 표 5개 + 변형 10 + configurator 2 ≈ 20 | 기법 5 × {Pure, +Orbis} + 변형 8 + concolic 2 + fuzzer 3 | baseline 3 × {±RSFuzz} + 변형 9 |
| 실행 예산 | 10 h | 24 h | 24 h | 24 h (학습 12 + fuzzing 12) |
| 반복 | 5회 평균 | 5회 평균 | 5회 평균 (버그는 5회의 합집합) | 5회 평균 (크래시는 합집합) |
| **CPU 시간 명시** | 없음 (추정 ~13,600 h, Table V만) | 없음 (추정 ~20,000 h) | **"18,000 hours"** (Table 3만) | 없음 (추정 ~10,000 h) |
| 장비 | Xeon Gold 6230R ×2 | Xeon Gold 6230 ×2 | Xeon Gold 6230R ×2, 256 GB | Xeon Gold 6230R ×1 |
| 통계 | Wilcoxon (Base vs TopSeed만) | Mann-Whitney (RQ1만, 48건) | Mann-Whitney (Table 3·4만, **p 평균**) + Pearson | Mann-Whitney (coverage만) |
| 비싼 실험의 대상 | **가장 큰 5개** (RQ2·RQ4·Discussion) | **5개** ("가장 큰 3 + 버그가 나온 3") | ablation은 15개 전체, KLEE만 | RQ2는 입력 100,000개, 재사용은 포맷별 가장 큰 2개 |
| 일반성 실험 | 3 프로그램 (Chameleon 논문의 것) | 4 프로그램 (Chameleon 논문의 것) | 4 프로그램 (Chameleon 논문의 것) | 2쌍 |

**공통 규모:**

- 벤치마크 12–17개, 전부 선행 연구에서 가져왔다.
- 5회 반복, 실행 1회당 10–24시간, 전체 10⁴ CPU-시간대, 장비 1대.
- 일반성 실험은 **다른 논문의 벤치마크 3–4개**로 한다. 이 규모로 Abstract·Conclusion에서 "generally applicable"이라고 주장한다.

**통계는 주 지표 하나에만 쓴다 (4/4).**

- 버그, ablation, 일반성, 하이퍼파라미터에는 검정이 하나도 없다.
- 효과 크기(effect size)는 0/4다.
- 표준편차는 도구마다 벤치마크를 통틀어 하나로 묶은 값(pooled)을 쓰거나 일부 벤치마크에만 쓴다.
- ASE26은 벤치마크별 p값의 **평균**을 보고했는데, n = 5 대 5에서 가능한 최소 p값 근처에 있다.

**규모 서술의 수사.** 규모를 숫자로 강조하는 논문은 1/4뿐이다 (ASE26 "required 18,000 hours ... which indicate that our experiments were conducted extensively"). 다른 논문은 baseline의 강함을 엄밀성의 근거로 든다: "Given that Symtuner is an arguably strong baseline, this choice ensures a rigorous evaluation" (ICSE26).

**부분집합 선택:**

- 비싼 실험은 "가장 큰 프로그램"에서 한다. 근거는 "larger potential for improvement"(ICSE25)이고, 이것은 향상이 가장 큰 곳을 고르는 것과 같다.
- ICSE26의 5개에는 최대 향상 사례(xorriso, +106.6%)가 들어 있다. 이 부분집합에서 Symtuner 대비 향상은 +34.0%로, 전체 12개에서의 +25.8%보다 크다.
- 사례 연구는 4/4가 **향상이 가장 큰 대상**을 고르고, 그 기준을 숨기지 않는다.

---

## 11. 장점·단점 비율

### 11.1 결과 문장 코딩

| ID | F | U | B | N | 계 | **U 비율** | Threats 밖 U 비율 |
|---|---|---|---|---|---|---|---|
| ICSE25 | 34 | 12 | 7 | 8 | 61 | 19.7% | 14.5% (8/55) |
| ICSE26 | 62 | 9 | 8 | 8 | 87 | 10.3% | 8.2% (7/85) |
| ASE26 | 66 | 8 | 10 | 6 | 90 | 8.9% | **2.5% (2/80)** |
| FSE26 | 54 | 13 | 1 | 17 | 85 | 15.3% | 12.7% (10/79) |
| **합계** | **216** | **42** | **26** | **39** | **323** | **13.0%** | **9.0% (27/299)** |

- **F + B = 74.9%, U = 13.0%.** 장점 문장이 단점 문장보다 **약 5.8배** 많다.
- U의 36%(15/42)는 Threats에 있다.
- **주 지표 하위절에는 U가 거의 없다.**
  - ASE26은 4.2–4.6(RQ 전부와 사례 연구)에서 **0/74**다.
  - ICSE26은 4.3·4.4에서 0이다.
  - Threats 밖의 U는 대부분 부차 분석(Discussion, 하이퍼파라미터, 재사용, 외부 계열 비교)에 있다.
- ICSE26은 U 9개 중 4개가 성능 손실이 아니라 "파라미터가 프로그램마다 다르다"는 동기 주장에 대한 반례다. 이것을 빼면 U는 5.7%다.

### 11.2 단점이 놓이는 곳

| 위치 | 단점 수 |
|---|---|
| Abstract | **0/4** |
| Introduction | **0/4** |
| Conclusion | **0/4** (future work도 0/4) |
| 별도 Limitations·Discussion 절 | 0/4 (ICSE25 Discussions는 장점만) |
| §3 Approach | ASE26만 1개 ("We acknowledge that some hidden options may not appear ... However, ... only 0.9% ... negligible") |
| §4 결과 하위절 | 논문당 2–10개, 주로 부차 분석 |
| Threats | 논문당 2–6문장, 85–175 words |

- **단점은 §4 안에만 있다.** Abstract·Intro·Conclusion은 §4의 단서를 모두 뺀 문장으로 요약한다 (§13.3).
- Threats는 **외적 타당도**(다른 엔진·벤치마크·문법) 위주다. **내적 타당도**는 0–1개다:
  - baseline 재구현·수정 (SymtunerAllP, RandF)
  - best-of-2 보고
  - 평가 프로그램에서 튜닝한 하이퍼파라미터
  - 고유 버그 판정 기준

### 11.3 표에는 있지만 본문에 없는 것

| ID | 제안 기법이 엄격히 진 주 표 셀 | 동률·비우위 셀 중 본문에 없는 것 | 그 외 |
|---|---|---|---|
| ICSE25 | 0 | 12 (factor 3개 baseline이 264=264 동률인데 "minimal"이라고만 씀, 동률에도 TopSeed 굵게) | Table VI 7행 중 5행이 RandSeed와 동률 |
| ICSE26 | 0 | 22 (전부 버그 수 동률) | 일반성 Venn에서 Chameleon만 덮은 분기 3/4 |
| ASE26 | 0 (Table 3–9) | Table 5 25셀 중 9셀 동률 | **Table 10에서 13셀 엄격한 패배** (ZigZagFuzz가 9/15 프로그램에서 고유 분기 우위), SOTA+Orbis < KLEE+Orbis 40/60 |
| FSE26 | 0 (Table 5의 Δ%) | 동률 4 + Table 4 동률 5 + 놓친 크래시 3셀 | 다른 계열 간 비교 (plain RandF > ProbF+RSFuzz 8/12)는 다루지 않음 |

- **주 지표 표에서 엄격히 진 셀은 4편 모두 0이다.** 지는 결과는 주 표가 아니라 부차 표(ASE26 Table 10)나 다른 계열 간 비교에만 있다.
  - 이 패턴의 일부는 **실제로 결과가 강하기 때문**이다.
  - 일부는 **벤치마크 선택**에서 나온다. ICSE25는 baseline이 이미 높은 커버리지를 내는 작은 프로그램(<1,000 분기)을 미리 제외했다.
- **0행은 지운다 (4/4).** 버그 표는 버그가 나온 벤치마크만 보여 준다: ICSE26 12개 중 3개, ASE26 15개 중 5개, FSE26 12개 중 7개.
- **동률에도 우리 열을 굵게 한다** (ICSE25). 캡션의 "best in bold" 규칙과 맞지 않는다.

### 11.4 가설 검증

사용자 가설: *"장점은 최대한 살리고 단점은 최소화하거나 defense 가능한 비치명적인 것만 드러내며, 주장을 좁히는 대신 유리한 새 주장으로 재프레이밍한다."*

| 가설 | 판정 | 근거 |
|---|---|---|
| 장점 최대화 | **맞음** | F+B 75%. 요약에서 단서를 모두 뺌 (§13.3). 지표·집계 방식을 유리한 쪽으로 고름 (§13.2 R9) |
| 단점 최소화 | **맞음** | U 13%, Threats 밖 9%. 드러낸 U에는 예외 없이 축소 장치가 붙음 (§12) |
| 비치명적인 것만 드러냄 | **대체로 맞음, 단서 있음** | 드러낸 U 42개 중 주 주장에 치명적인 것은 0개, "중간"이 6–7개다 (ICSE25 factor 동률, ASE26 Threats의 엔진 일반성, FSE26 입력 수 감소). 드러내는 단점은 둘 중 하나다: **(a) 표에 이미 보여서 숨길 수 없는 것**, 또는 **(b) 리뷰어가 물을 것이 뻔한 것**(분산, 깊은 경로 탐색, 오버헤드). 표에도 없고 묻지도 않을 것은 쓰지 않는다: 자기 오버헤드 실측 0/4, 평가 프로그램에서의 튜닝 0/4 |
| 주장을 좁히지 않고 재프레이밍 | **맞음** | 4편 모두 주장을 좁히는 문장이 없다. 오히려 3–4개 프로그램으로 "generality"를, 수렴한 결과로 "complementary"를 주장해 넓힌다. 약한 결과는 필요성·trade-off·확장성으로 바꿔 쓴다 (§13) |

**가설에 덧붙일 두 가지:**

1. **주 결과 자체는 실제로 강하다.** 주 지표에서 엄격히 진 셀이 없다. 수사는 주 결과를 부풀리기보다는 **부차 결과의 약점을 관리하는** 데 쓰인다.
2. **가장 효과적인 장치는 선제 점검이다 (§13.1 R7).** 리뷰어가 물을 약점을 RQ나 분석으로 먼저 질문하고, 실험으로 답해 장점으로 바꾼다.
   - "To examine whether ParaSuit's iterative approach ... limits its ability to explore deeper paths, we compared it with Klee24h" (ICSE26) → "123.9% deeper"
   - ICSE25 Discussion의 KLEE10h 비교 → "covers 95%"

   약점을 감추지 않고 **약점에 대한 질문을 먼저 가져간다.**

---

## 12. 단점을 서술하는 장치

### 12.1 장치 목록

| 장치 | 출현 | 원문 |
|---|---|---|
| **D1 축소 수량화** ("only") | 4/4 | "missed **only** 15 branches" (ICSE25) / "missed **only** 7.5 branches on average" · "account for **only** 13.3%" · "**only** a 1% drop" (ICSE26) / "while missing **only** one bug" · "by **only** about 1%" (ASE26) / "while missing **only** two" (FSE26) |
| **D2 양보절** (약점은 종속절, 장점은 주절) | 4/4 | "**While** the standard deviation of TopSeed was slightly higher than Base, this difference was negligible given the significant performance improvements" (ICSE25) / "**Despite** the effectiveness of Kleenew, it still covered 43.1% fewer branches" (ICSE26) / "**Despite** the negative side effect, integrating RSFuzz resulted in noticeably higher line coverage" (FSE26) / Threats 첫머리 "**Although** these benchmarks cover a broad spectrum ..." |
| **D3 완화 형용사** | 4/4 | modest, minimal, negligible, slightly, comparable, relatively stable, generally |
| **D4 원인 귀속** (벤치마크·설계·baseline 탓) | 4/4 | 벤치마크: "on large benchmarks, which have a greater potential for improvement" (ICSE25), "An exception was observed for the CSV benchmarks" (FSE26) / 설계: "This reduction occurs because RSFuzz allocates half of the total testing budget" (FSE26) / baseline: "primarily because they leverage diverse inputs generated by mutating manually provided seeds" (ASE26) |
| **D5 손실의 긍정 표현** | 2/4 | "covers, on average, 95% of the branches" (= 5% 놓침, ICSE25) / 동률을 "maintained the same coverage" (FSE26) |
| **D6 집계로 가리기** | 4/4 | 벤치마크를 통틀어 묶은 SD 하나 (ICSE26: Kleefix 41 < ParaSuit 57인데 "relatively stable") / 고유 분기만 보고하고 전체 커버리지는 쓰지 않음 (ASE26: ZigZagFuzz 전체 64,356 > KLEE+Orbis 57,558) / 합계의 비율을 "average"라고 부름 (ICSE26, FSE26) |
| **D7 유리한 예만 인용** | 3/4 | 손실이 가장 작은 sqlite("only 15")를 인용하고 가장 큰 patch(139)는 쓰지 않음 (ICSE25) / 재사용 격차 4개 중 1개만 수치로 씀, SD는 12개 중 2개 벤치마크만 씀 (FSE26) |
| **D8 침묵** (표에는 있고 본문에는 없음) | 4/4 | §11.3의 동률·패배 셀 |
| **D9 Threats로 보내기** + "may" + 완화 근거 | 4/4 | "Its performance may vary when applied to other symbolic executors." / "However, they may not generalize to other symbolic execution engines." |
| **D10 0행 지우기** | 4/4 | 버그가 0인 벤치마크를 버그 표에서 뺌 |
| **D11 자기 비용 생략** | 4/4 | 제안 기법의 오버헤드를 §4에서 따로 측정한 논문이 없다. ASE26의 Guide 오버헤드(예산의 9.6%)는 §3에만 있다. ICSE26의 추출 단계 비용과 FSE26의 입력당 생성 비용은 보고하지 않는다 |

### 12.2 단점 문장의 틀

4편에서 반복되는 구조는 다음과 같다.

```text
[양보절: 약점 + 축소어(D1/D3)] + [주절: 장점 또는 원인 귀속(D4)] + [함의: 필요성·새 주장(§13)]
```

- "**While** X missed **only** N branches ..., **it exclusively covered** M branches that ... failed to reach."
- "**Despite** the negative side effect, integrating X resulted in noticeably higher ... **This finding highlights the effectiveness of X, even when accounting for** the time spent ..."
- "**An exception was observed** for <벤치마크 군>, where ... **However, on 10 out of 12 benchmarks**, ..."
- Threats: "(k) <사실>. **Although** <완화 근거 / 다른 절의 결과>, **may not** ..."

약점 문장이 단독 주절로 끝나는 경우는 Threats 밖에서 거의 없다. ICSE26 "The standard deviations ... were as: ParaSuit (57), ..., Kleefix (41)"이 예외인데, 바로 다음 문장이 "This indicates that our results were relatively stable"이다.

---

## 13. 재프레이밍 패턴

### 13.1 약점 → 새 주장

| 패턴 | 이동 | 원문 |
|---|---|---|
| **R1 약점 → 우리 설계의 필요성** | baseline이나 단순 변형의 불안정·실패를 우리 설계가 필요한 근거로 쓴다 | "Surprisingly, for the dd program, Learch+RandSeed covered 63.2% fewer branches ... This inconsistency of RandSeed **underscores the necessity of our approach**" (ICSE25) / Kleenew가 이전되지 않는다는 결과를 "**This indicates that trying multiple parameter sets over short periods is more efficient** than ... a single fixed parameter setting" (ICSE26) |
| **R2 손실 → trade-off·대안** | 지는 설정을 "다른 목적에는 실용적인 선택"으로 바꾼다 | "**Unquestionably**, RSFuzz achieves the best results when ... **However, if the goal is to reduce the overhead** ..., reusing sequences ... is a **practical and effective alternative**." (FSE26) / hidden option 1%를 "Therefore, we adopt a **cost-effective strategy**" (ASE26) |
| **R3 수렴·혼재 → 상보성** | 이득이 겹치거나 상대가 이기는 부분을 "서로 보완한다"로 쓴다 | "These results show that Orbis is **complementary to existing** symbolic execution techniques" (ASE26, SOTA+Orbis가 KLEE+Orbis보다 낮은 상황) / "We present RSFuzz, a **complementary** technique" (FSE26, 다른 계열 간 비교를 피함) |
| **R4 불안정 → 적응성** | 수렴하지 않는 결과를 "적응한다"로 쓴다 | "the weight for 'uniqueness' fluctuated over time. These observations suggest that our learning approach **adaptively refines** ..." (ICSE25) |
| **R5 혼재한 ablation → "둘 다 필수"** | 벤치마크마다 중요도가 바뀌는 결과를 둘 다 필요하다는 근거로 쓴다 | "Coverage improvements from each stage varied across benchmarks ... Although both ... are essential, the grouping algorithm has a more pronounced impact" (ICSE25) / "the relative importance ... varied ... These findings demonstrate that **both** the Select and Capture steps **are essential**" (FSE26) |
| **R6 민감도 → 기본값의 정당화** | 파라미터 값에 따라 성능이 크게 떨어지는 결과를 기본값이 옳다는 근거로 쓴다 | "a η_time of 60 seconds led to a 10.9% drop ..., indicating that an excessively short time budget ... can degrade performance" (ICSE25) / 데이터 1점으로 "generally robust to such variations (e.g., only a 1% drop ...)" (ICSE26) |
| **R7 선제 점검** (가장 중요) | 리뷰어가 물을 약점을 먼저 질문하고, 실험으로 답해 장점으로 만든다 | "**To examine whether** ParaSuit's iterative approach ... **limits its ability to explore deeper paths**, we compared it with Klee24h" (ICSE26) / KLEE10h 비교 → "TopSeed's iterative runs can maximize branch coverage" (ICSE25) |
| **R8 공백 → 확장성** | 아직 못 얻은 이득을 "더 좋아질 수 있다"로 쓴다 | "ParaSuit **can also be augmented with prior knowledge, which further enhances** its effectiveness" (ICSE26, 기본 설정이 5.7%를 놓친다는 뜻) / "incorporating more precise control-dependence analysis **could further improve** performance" (ASE26) |
| **R9 확대해 보이는 지표 고르기** | 작은 차이를 크게 보이는 단위로 보고한다 | "**3.5 times more unique branches**" (ICSE26, 전체 커버리지 향상은 +1.0–9.8%) / 상대 증가 "323.0%"만 쓰고 절대 OB 커버리지는 쓰지 않음 (ASE26) / 합계 비율과 벤치마크 평균 중 큰 쪽 |
| **R10 기존 버그 → 검증** | 신규성이 약하다는 사실을 재현성의 증거로 쓴다 | "We manually confirmed that several of these reproducible crashes **correspond to previously reported bugs**" (FSE26) |
| **R11 규모·강한 baseline → 엄밀성** | 실험 규모나 baseline 선택 자체를 엄밀성의 증거로 쓴다 | "which indicate that our experiments were **conducted extensively**" (ASE26) / "this choice **ensures a rigorous evaluation**" (ICSE26) |

### 13.2 baseline의 약점을 주장으로 (B 문장)

B 문장(26개)은 **baseline의 한계 = 우리 접근의 동기**라는 틀로 쓴다.

- "**This finding highlights a key limitation of** Symtuner—its use of a predefined configuration regardless of the target program." (ICSE26, 두 baseline끼리의 결과)
- "The results of Symtuner and SymtunerAllP **underscore the complexity of manual configuration**." (ICSE26). SymtunerAllP의 파라미터 공간 70개는 저자가 직접 정의했는데, Threats에서 다루지 않는다.
- "AAQC alone covered only 597 branches in sqlite ... However, integrating Orbis with AAQC significantly improved coverage" (ASE26). baseline의 병리적 이상치가 헤드라인 배율이 된다.

### 13.3 요약은 단서를 뺀다

| ID | §4의 단서 | Abstract·Intro·Conclusion |
|---|---|---|
| ICSE25 | factor 동률, 작은 프로그램에서 "modest", Learch는 버그 증가 0, 일반성은 3개 프로그램 | "significantly enhances four distinct cutting-edge techniques ... in terms of branch coverage and bug-finding abilities" |
| ICSE26 | 버그는 12개 중 3개 프로그램에서만 나왔고 7/11이 gcal, 개발자 확인은 1개 | "Remarkably, ParaSuit identified 11 unique bugs" |
| ASE26 | "may not generalize to other symbolic execution engines", fuzzer가 전체 커버리지에서 이김 | "significant gains in branch coverage and bug detection beyond existing approaches" |
| FSE26 | 벤치마크별 평균 향상 3.3–4.0%, 동률 4개, 크래시가 늘어난 것은 6/12 | "markedly enhances" |

- **§4에서 "may"로 쓴 것은 요약에 없다 (4/4).** 요약 문장은 §4 문장에서 양보절을 지운 주절이다.
- 요약 수치는 대개 **합계의 비율**이다. 벤치마크별 평균이나 중앙값보다 크다 (ICSE26 25.8% vs 평균 21.8% · 중앙값 14.1%, FSE26의 순위가 뒤바뀜).

### 13.4 따라 하면 안 되는 것

4편 모두 다음이 있다. 이것은 수사가 아니라 **오류**이고, 리뷰어가 하나만 찾아도 전체 수치의 신뢰를 잃는다.

| 유형 | 예 |
|---|---|
| 본문-표 수치 불일치 | ICSE25 gawk 18,512 vs 25,124 / ICSE26 trueprint 28.7% vs 27.6% / ASE26 OB 범위 8,080 vs 16,616, Table 9 합계 3,840,978 vs 행 합 8,902,371 |
| 비율 방향 혼동 | ICSE25 "11.3% lower" (실제 10.1% 낮음, 11.3%는 반대 방향) / ASE26 "to 323.0%" vs "323.0% increase" |
| 개수 불일치 | ICSE25 기법 수 four/three/four / ICSE26 sampling 알고리즘 three/four/five/six |
| 근거 없는 Threats 완화 | ICSE25 "Section IV-E demonstrates stable performance across ... CREST" (CREST로는 sweep하지 않음) |
| 통계 비정합 | FSE26 평균이 같은 4쌍(728.0/728.0)에서도 "p < 0.05 for all 12" |

---

## 14. 우리 논문(CoEP)에 적용

### 14.1 그대로 가져올 것

| 항목 | 적용 |
|---|---|
| 비교는 표, 설명은 그림 (§9.2) | Table III(RR·RPS)와 Table IV(비용)는 표로 둔다. 그림은 비용 곡선(N*), overview, 규칙 예시로 한정한다 |
| 비용 플로트 | 4편에 비용 플로트가 없는 것은 비용이 그들의 주장이 아니기 때문이다. **우리는 비용이 주장이므로** Table IV와 Fig. cost를 둔다. 페이지가 모자라면 Fig. cost를 빼고 N*를 표에 남긴다 |
| 통계는 주 지표에 + 예외 명시 | 이미 McNemar·Wilcoxon과 "An exception is ... p = 0.78"이 있다. 4편보다 엄격하므로 유지한다 |
| 규모 한 문장 (R11) | 프로그램 수, 모델 호출 수, $, CPU 시간을 한 문장으로 쓴다 ("generating Table III required ... calls and ... CPU-hours"). 4편은 10⁴ CPU-시간 규모이고, 우리는 LLM 호출 수와 비용이 그에 대응하는 규모 지표다 |
| 단점 문장의 틀 (§12.2) | 양보절 + 주절 + 함의. 예: "**While** \coepL repaired 93.8% of R2 where PyDex repaired 97.8%, **the escalation of** \coepLF **recovered most of them**, ... This finding highlights the role of the fallback" (현재 원고가 이미 이 틀이다) |
| 동률 굵게 규칙 | 캡션에 "ties included"를 명시했다. ICSE25처럼 동률인데 우리 열만 굵게 하지 않는다 |

### 14.2 우리 약점의 위치 정하기

| 우리 결과 | 치명도 | 4편식 처리 | 권장 |
|---|---|---|---|
| **CS1 테스트 과적합** (held-out 테스트에서 지역 수리가 떨어짐) | **치명적**. AAAI 리뷰어가 직접 지적함 | 4편에는 같은 상황의 선례가 없다. 치명적인 단점은 애초에 드러나지 않았다 | **R7 선제 점검.** "Do the repairs generalize beyond the instructor's tests?"를 RQ나 하위절로 세운다. 차등 테스트(B)를 **방법의 일부**로 넣고, held-out 생존율을 결과로 보고한다. 남는 격차는 D2 틀로 쓴다. **D8(침묵)은 쓰지 않는다**: 리뷰어가 물었던 것이므로 다시 확인한다 |
| 같은 풀로 구축·평가 (seen/unseen만 있음) | 중간. 리뷰어가 지적함 | ICSE25·ICSE26도 하이퍼파라미터를 평가 프로그램에서 튜닝했지만 밝히지 않았다 | 시간 분할·split 실험으로 대체한다 (R7). 이력이 적을 때 CF에서 떨어지는 것은 D4(참조 프로그램 부족 탓) + fallback으로 회복된다는 점 + **"class가 커질수록 싸진다"는 배포 곡선**(R2: 새 주장)으로 쓴다 |
| LLM_Direct의 패치가 더 작음 (공통 프로그램에서) | 중간. RPS 우위의 출처가 달라짐 | R3/R1 | "작은 패치는 per-submission 호출이 아니라 최소 편집 참조 π(b)에서 온다. CoEP는 π(b)를 유지하면서 호출 대부분을 없앤다." 패치 크기 주장을 **아키텍처 대 PyDex**에서 **π(b) 설계**로 옮기고, 아키텍처의 기여는 RR(+8–19 pp)과 비용에 둔다 |
| \gm에서 ATT가 PyDex보다 느림 | 낮음 | D2 + D4 | 현재 원고("the one measure on which the per-submission arm won ... depends on how fast the model answers")를 유지한다 |
| 규칙의 RR 기여가 작음 (Synthesize ablation) | 낮음 | R5 | 현재 원고처럼 "rules carry precision, transplant carries breadth"로 쓴다 |
| C6 RPS > 1 | 낮음 | D4 | 2개 참조 프로그램과 짧은 정답이라는 벤치마크 특성으로 설명한다 |

### 14.3 수위

- **Abstract·Intro·Conclusion에는 약점을 넣지 않는다 (4/4 관행).** 다만 §4의 단서와 **모순되는** 요약 문장은 쓰지 않는다. 예를 들어 "all assignments"라고 쓰면 C6 등 예외와 부딪히므로, 수치 범위를 그대로 쓴다.
- Threats는 (1)(2)(3) 형식을 유지한다. 리뷰어가 짚은 항목(테스트 적정성, 같은 풀)은 **본문 실험으로 이미 답했다는 완화 근거**와 함께 둔다.
- §13.4의 오류는 [floats.md](floats.md) §7처럼 모든 수치를 한 산출물에서 만들어 막는다.

---

## 부록 A. 원문 발췌 (역할 태그)

**RQ 목록 (E-0)**

> **[ICSE25]** In this section, we evaluate the effectiveness of TopSeed based on the following research questions:
> 1) **Effectiveness:** How effectively can TopSeed enhance state-of-the-art techniques for symbolic execution in terms of branch coverage and bug-finding capability?
> 2) **Efficacy of Each Stage:** How effectively does each stage in TopSeed contribute to improving the performance?
> 3) **Generality:** Is TopSeed applicable to a concolic testing technique, a variant of dynamic symbolic execution?
> 4) **Impact of Hyperparameters:** How do hyperparameter values affect the performance of TopSeed?
>
> We implemented TopSeed on top of KLEE-2.1 [4], an actively maintained symbolic executor that incorporates diverse techniques [11], [15], [17], [18], [26]. All experiments were conducted on a single Linux machine equipped with two Intel Xeon Gold 6230R processors.

> **[ICSE26]** We evaluate ParaSuit to answer the following research questions:
> - **Branch coverage**: To what extent does ParaSuit improve branch coverage over manual and user-configured tuning methods?
> - **Bug-finding ability**: How effectively can ParaSuit find unique bugs compared to existing tuning approaches?
> - **Efficacy of two stages**: Does our parameter selection algorithm outperform naive approaches? Is our value sampling stage more effective than generic sampling methods?
> - **Analysis of self-configuration**: Which parameters are most impactful? How do they and their values vary by program? Does the new setting sampled by ParaSuit surpass existing baselines?
> - **Generality**: Can ParaSuit be applied to concolic testing tools?

**Settings (E-1)**

> **[ICSE25 · Benchmarks.]** We used 17 open-source C programs in Table IV, which displays the number of lines and branches for each program. To construct our benchmark suite, we initially collected all available programs used in the experiments by the four baselines [4], [11], [15], [18]. From these, we selected 17 program benchmarks for evaluation based on two filtering criteria among them: (1) we filtered out smaller programs with fewer than 1,000 total branches, as the baselines achieved high code coverage for these programs even without seeding (e.g., tty-8.31). (2) we also omitted programs (e.g., objcopy-2.36) where all baselines managed to cover less than 2.0% of total branches over 10 hours, indicating that the baselines failed to test the core functionality of these programs and only test error handing functions. Note that for our 17 programs, at least one of the four baselines was able to cover more than 22.5% of total branches on average within 10 hours.

> **[ASE26 · Other Settings.]** For all experiments, we tested each baseline with and without Orbis's guidance on each benchmark using a 24-hour budget, repeating the same experiment five times. We then reported the average results, which indicate that our experiments were conducted extensively. For instance, generating the coverage results reported in Table 3 required 18,000 hours when using a single CPU core (i.e., 24 hours × 5 trials × 15 benchmarks × 5 baselines, each tested with and without Orbis). Additionally, to ensure a fair comparison with Orbis, we evaluated baselines under both settings: (1) a single uninterrupted 24-hour run and (2) repeated shorter runs whose results were merged, matching the execution setting of Orbis. We reported the better-performing result for each baseline.

**주 지표 (E-2)**

> **[ICSE26 · H + Q + N + S]** Table 2 demonstrates that ParaSuit consistently outperforms both static and user-defined configuration approaches in terms of branch coverage across all 12 benchmarks. We used gcov to collect the covered branches for each benchmark. In summary, ParaSuit covered 25.8% more branches than Symtuner, 97.4% more than Kleefix, 46.8% more than RandSuit, and 95.6% more than SymtunerAllP. Notably, ParaSuit, our self-configuring approach, consistently achieves higher branch coverage than Symtuner, which relies on manually defined configurations. For instance, in the case of the largest program xorriso, ParaSuit achieved 106.6% higher branch coverage than Symtuner, the second-best baseline—making the largest difference across all benchmarks. Interestingly, in grep, Symtuner even covered 2% fewer branches than RandSuit, which naively selects parameters and their corresponding values. This finding highlights a key limitation of Symtuner—its use of a predefined configuration regardless of the target program.

> **[ICSE25 · S + T]** Running each baseline with a random seed selection strategy (RandSeed) typically resulted in higher branch coverage compared to running it without seeds (Base). However, RandSeed sometimes underperformed relative to Base. ... Surprisingly, for the dd program, Learch+RandSeed covered 63.2% fewer branches than Learch+Base. This inconsistency of RandSeed underscores the necessity of our approach (Algorithm 3) to achieve stable and high coverage across various benchmark programs.
>
> These results in Table V were statistically significant: on 16 of the benchmark programs, the p value between Base and TopSeed across the four baselines was less than 0.05 according to the Wilcoxon signed-rank test. An exception occurs in the factor program, where the gap in branch coverage between TopSeed and Base across four baselines was minimal. The standard deviations of branch coverage across four baselines on our benchmarks were as follows: Base (38.6), RandSeed (73.1), and TopSeed (52.0). As expected, RandSeed showed the highest variability. While the standard deviation of TopSeed was slightly higher than Base, this difference was negligible given the significant performance improvements achieved by TopSeed.

**부 지표 (E-3)**

> **[ICSE26]** Table 3 shows the effectiveness of ParaSuit in identifying unique bugs compared to other baselines. To obtain these results, we collected all test-cases flagged by KLEE as bugs, denoted as the "*.err" files. We then re-executed the original binary of each program with these potential bug-triggering test-cases and retained only those that were reproducible. A bug-triggering test-case was considered unique if its error location reported by KLEE differed from others. ... In total, ParaSuit succeeded in detecting 11 unique bugs across three of the 12 programs: gcal, gawk, and combine. This count is 4 more than the state-of-the-art Symtuner; ... Notably, ParaSuit did not miss any bugs that other baselines detected, while it successfully identified four additional bugs. All bugs discovered by ParaSuit were reported to the program developers ...

**Ablation (E-4)**

> **[ASE26 · 왜 이겼는지]** We investigated why Orbis notably outperformed CitConst. The key difference is their objective. As a state-of-the-art CIT technique, CitConst systematically exercises option combinations while minimizing the number of generated option arguments. Consistent with this objective, it selected substantially more options per option argument than Orbis (37.4 on average, 9.4× more). When applied to symbolic execution, however, these large option arguments often resulted in ineffective executions: 68.6% either achieved zero branch coverage or terminated before exhausting the time budget, frequently due to conflicting or ineffective option combinations. ... In contrast, Orbis continuously evaluates the effectiveness of option arguments during symbolic execution and repeatedly reuses those that prove effective in improving exploration.

**일반성 (E-5)**

> **[ICSE25]** We examined if our seeding approach is applicable to concolic testing [1], [3], a major variant of symbolic execution. We integrated TopSeed with CREST [28], a popular concolic testing tool that incorporates diverse techniques [29], [30], [31], [32]. Additionally, we evaluated TopSeed's potential to enhance the performance of Chameleon [32], a state-of-the-art search strategy implemented on CREST. For each baseline, we reported the number of branches covered and bugs identified across the three large benchmarks used in [32]. ... On average, TopSeed increased branch coverage by 7.8% compared to CREST and 3.9% compared to Chameleon. Interestingly, with the seeding provided by TopSeed, the basic concolic testing tool CREST occasionally outperformed the advanced, unseeded Chameleon on the sed program. ... These results indicate that TopSeed is versatile and can be generalized to other symbolic execution tools, significantly enhancing both branch coverage and bug-finding abilities.

**사례 연구 (E-6)**

> **[ASE26 · 4.6 Case Study]** To illustrate how Orbis guides symbolic execution to achieve higher total branch coverage, we conducted a case study on the diff program. Particularly, we analyzed an effective test-case ("diff -p -0") that covers 471 branches in a single execution, accounting for 48.3% of the total coverage achieved by KLEE within a 24-hour budget. We then compared the average time required by KLEE with and without Orbis's guidance to generate this test-case. ... Empirically, KLEE with Orbis generated the test-case "diff -p -0" in just 7.1 seconds. ... In contrast, KLEE alone required 9,012.7 seconds to generate the entire argument "-p -0" symbolically—approximately 1,269× longer.

**Threats (E-7)**

> **[ICSE25 · G. Threats to Validity]** (1) TopSeed was evaluated using KLEE and CREST, which are prominent symbolic executors. Its performance may vary when applied to other symbolic executors. (2) The three hyperparameters in TopSeed, used for running the symbolic execution engine KLEE, were determined through trial and error. Although Section IV-E demonstrates stable performance across our benchmark suite and another symbolic execution engine, CREST, these settings may not be optimal for other programs or symbolic engines. (3) We used 17 carefully selected benchmarks. While this benchmark suite includes all major programs used in the four baselines, it may not sufficiently evaluate the full scope of TopSeed's performance.
