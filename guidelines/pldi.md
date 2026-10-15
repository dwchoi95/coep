# PLDI 2027 — 요구사항과 PLDI 선행 연구 5편 분석

[section/](section/)의 문서들은 SE 학회 논문 4편(ICSE/ASE/FSE)을 분석한 것이다. 이 문서는 PLDI가 무엇을 요구하는지, 그리고 우리 Related Work에 있는 PLDI 논문들이 어떻게 쓰였는지를 정리하고, CoEP 원고와의 차이를 짚는다.

**분석 대상**

| 약칭 | 논문 | 학회 | CoEP와의 관계 |
|---|---|---|---|
| AutoGrader | Singh, Gulwani, Solar-Lezama, *Automated Feedback Generation for Introductory Programming Assignments* | PLDI'13 | 강사가 손으로 쓰는 error model(재작성 규칙). **CoEP는 이 error model을 과제마다 합성한다.** 현재 원고에 인용이 없다 |
| CLARA | Gulwani, Radiček, Zuleger, *Automated Clustering and Program Repair for Introductory Programming Assignments* | PLDI'18 | 정답 프로그램 군집화와 수리 |
| Sarfgen | Wang, Singh, Su, *Search, Align, and Repair* | PLDI'18 | 검색, 정렬, 이식. CoEP의 참조 이식과 가장 가깝다 |
| SemCluster | Perry, Kim, Samanta, Zhang, *SemCluster* | PLDI'19 | 의미 기반 군집화. CoEP의 편집 스크립트 군집화와 대비된다 |
| TypeCon | Mündler et al., *Type-Constrained Code Generation with Language Models* | PLDI'25 | LLM 기여를 PL 학회에서 어떻게 쓰는지 보여 주는 최근 사례 |

---

## 0. 핵심 결론

1. **PLDI 논문의 기여는 PL 객체다.** 동기는 응용(교육, LLM 오류)이지만, 기여 목록 첫 줄은 언어·의미론·탐색 공간·인코딩이다.
   - AutoGrader: error-model 언어 EML과 Sketch로의 환원
   - CLARA: 프로그램 모델, 동적 매칭 관계, ILP
   - Sarfgen: 임베딩 거리와, 정렬을 argmin 문제로 정식화한 것
   - SemCluster: 모델 카운팅으로 정의한 의미 특징
   - TypeCon: prefix automaton과 type inhabitation
   - CoEP 원고의 기여는 반대 구도다. 관찰(반복 수리), 비용 상각, 평가가 중심이다.
2. **형식 요소는 짧아도 된다. 하지만 성질을 정확히 진술해야 한다.**
   - 형식 비중: AutoGrader 약 27%, CLARA 약 30%, Sarfgen 약 10%, SemCluster 약 15%, TypeCon 약 40%.
   - 정리: AutoGrader는 종료성 정리 1개(증명 세 문장), CLARA는 건전성 정리 1개와 보조정리 1개, TypeCon은 보조정리 여러 개다. Sarfgen과 SemCluster에는 정리가 없다.
   - 공통점: 보장의 범위를 정확히 한정한다. 예: "guarantees only that repairs are correct over a given set of test cases"(CLARA), "upon termination"(TypeCon).
3. **평가는 추상화를 뒷받침하는 역할이다.**
   - 다섯 편 모두 명시적 RQ 목록이 없고, 문단 제목으로 주장을 세운다.
   - 통계 검정이 있는 논문은 없다(SemCluster와 TypeCon은 분산 보고도 없다). 베이스라인은 0–3개다.
   - CoEP의 평가(5개 RQ, McNemar·Wilcoxon, held-out, split)는 이들보다 훨씬 강하다. **평가가 약점이 될 가능성은 낮다. 약점은 "PL 기여가 무엇인가"다.**
4. **LLM은 신뢰하지 않는 오라클로 추상화한다(TypeCon).** 보장은 LLM과 무관하게 성립해야 한다("any LLM"). CoEP에서는 모든 후보(규칙, 이식, fallback)가 같은 수락 검사 T⁺를 통과해야 하므로 같은 구도를 그대로 쓸 수 있다.
5. **한 실행 예제를 논문 전체에 관통시킨다(5/5).**
   - 섹션 구성: Overview 2–3쪽 → 형식 모델 → 알고리즘·인코딩 → 짧은 구현 → 평가 → 관련 연구(약 1쪽).
   - CoEP 원고에는 Overview가 없다. 실행 예제(cAPS lOCK)는 Preliminaries에서 한 번 쓰고 끝난다.

---

## 1. PLDI 2027 투고 요건 (CFP)

| 항목 | 요건 | 원고 상태 |
|---|---|---|
| 템플릿 | `\documentclass[acmsmall,screen,review,anonymous,nonacm]{acmart}`, 단일 단, 10pt, 텍스트 블록 5.478×7.884 in | **적용함** |
| 분량 | 본문 20쪽 이하(AI Use 포함). Data-Availability Statement, 참고문헌, 부록은 제외 | 현재 17쪽(AI Use까지) |
| 인용 | 번호식이나 저자-연도 둘 다 가능 | ACM-Reference-Format(저자-연도) |
| 이중맹검 | 저자·소속 생략. 자기 연구는 3인칭으로 인용. 공개 코드는 URL 없이 인용하거나 익명 링크 사용 | anonymous 옵션. 아티팩트는 익명 미러. MENTORED(자기 연구)는 3인칭 |
| **AI Use** (2027 신설) | AI 도구로 코드·증명·데이터·테스트·산출물을 만들었다면 본문에 "AI Use" 절이나 단락을 둔다. 분량에 포함 | **초안 넣음, 저자 확인 필요** (`% TODO(authors)`) |
| **Data-Availability Statement** (신설) | 참고문헌 바로 앞에 둔다. 분량 제외. 아티팩트의 성격·한계·AE 제출 여부 | **넣음, AE 계획은 저자 확인 필요** |
| 기계화 증명 | 주요 기여라면 제출 시 함께 낸다 | 해당 없음 |
| Reserve reviewer (신설) | 시니어 저자 1명이 reserve reviewer로 등록하고 TPMS에 논문 5–10편 업로드 | **원고 밖: 저자가 처리** |
| 심사 | 1라운드(정확성·중요성·독창성·명료성) → 저자 응답(2/16–18) → 조건부 채택 → 2라운드(수정 확인) | |
| 마감 | **2026-11-12 AoE** (변경 불가) | |
| 범위 | PL 설계·구현·이론·응용·성능. 실증 논문은 SIGPLAN Empirical Evaluation Guidelines를 따르기를 권장 | |

---

## 2. 논문별 요약

### 2.1 문제 설정과 핵심 통찰

| 논문 | 동기 | PL로의 전환 | 핵심 통찰(원문) |
|---|---|---|---|
| AutoGrader | MOOC, 포럼의 무익한 동료 피드백 | 두 "simplifying assumption"(명세를 안다, 오류는 예측 가능하다) 뒤에 PL 과제(동치 검사, 오류 모델, 조율된 다중 수정) | "reduces the problem of finding minimal corrections … to the problem of synthesizing a correct program from a sketch" |
| CLARA | 피드백 비용, MOOC | §2에서 "inspired by the notion of a simulation relation" | "use the existing correct student solutions to repair the incorrect attempts"; "repair … as a generalization of the clustering" |
| Sarfgen | MOOC 규모의 자동 피드백 | 세 질문(Search, Align, Repair) | "reduce the alignment problem to a distance computation problem" |
| SemCluster | 군집화가 문법에 과민함("Clara generates 51 clusters for … 4 different solution strategies") | 입력 공간 분할과 데이터 흐름 | "the essence of a solution … lies in the way the problem space is partitioned" |
| TypeCon | 컴파일 오류의 94%가 타입 오류 | 타입 시스템은 CFG로 표현할 수 없음 → prefix automaton | "a sound approach to enforce well-typedness on LLM-generated code" |

**공통 패턴:** 동기 문단(응용) → **"key observation/insight" 한 문장** → 그 통찰을 PL 객체(언어, 관계, 거리, 오토마톤)로 바꾸는 문장 → 기여 목록(기법 → 구현·인스턴스화 → 평가).

### 2.2 형식 요소

| 논문 | 정의·의미론 | 정리 | 증명 | 알고리즘 |
|---|---|---|---|---|
| AutoGrader | MPY/M̃PY 문법, 가중 집합 의미론, EML(재작성 규칙), Def 1–2(well-formed) | Thm 1 종료성 | 세 문장 | CEGISMIN, 변환 T_E |
| CLARA | 프로그램 모델(위치, 갱신 함수, trace 의미론), 매칭 관계 ∼_I, 지역 수리, ILP | Lemma 4.6, Thm 5.3 건전성 | 스케치 | Match, Repair |
| Sarfgen | 위치 인식 특징 벡터, 거리(식 1–2), α-변환 argmin(식 3–5) | 없음(복잡도 언급만) | — | Alg 1(23줄) |
| SemCluster | 프로그램 모델, 입력 동치류, 값 변화 | 없음 | — | Alg 1–2 |
| TypeCon | prefix language/property, 코어 계산 L_B, 타이핑 규칙 | Lemma 1–7, Cor 4 | 본문과 부록 | Alg 1(LLM과의 diff 강조), Alg 2 |

**교훈:**

- 형식은 "가르치는 표기"다. 예제로 도입한 뒤 정의한다.
- 정리는 소수의 핵심 성질만 다룬다: 종료성, 건전성, 동치 관계, 포함 관계.
- 못 보장하는 것은 직접 쓴다: "incomplete", "only over a given set of test cases".

### 2.3 섹션 구성 (본문 대비 비율)

| 섹션 | AutoGrader | CLARA | Sarfgen | SemCluster | TypeCon |
|---|---|---|---|---|---|
| Intro | 14% | 11% | 13% | 12% | 10% |
| **Overview / 동기 예제** | **22%** | **19%** | **15%** | **13%** | **15%** |
| 형식 모델·기법 | 37% | 32% | 27% | 30% | 43% |
| 구현 | (평가에 포함) | 2% | (평가에 포함) | 4% | — |
| 평가 | 14% | 27% | 30% | 33% | 21% |
| 관련 연구 | 12% | 9% | 9% | 5% | 4% |

CoEP 원고(본문 약 16쪽, PDF에서 실측):

| 섹션 | 분량 | 비율 |
|---|---|---|
| Intro | 2.0쪽 | 12% |
| Preliminaries(일반 알고리즘, 한계 측정, 목표) | 2.2쪽 | 14% |
| Approach | 4.0쪽 | 25% |
| Experiments | 6.8쪽 | 43% |
| Related | 0.8쪽 | 5% |

→ **Overview가 없고 평가 비중이 PLDI 평균의 1.5–2배다.**

### 2.4 평가 관행

| 항목 | 다섯 편의 관행 | CoEP |
|---|---|---|
| RQ 목록 | 0/5. 문단 제목으로 주장한다(Performance, Number of Corrections, …) | 5개 RQ |
| 베이스라인 | 0(AutoGrader), 1(CLARA, Sarfgen), 3(SemCluster), Vanilla만(TypeCon) | Refactory, PyDex, LLM_Direct |
| 통계 | 0/5 | McNemar, Wilcoxon, Wilson |
| 실패 분석 | 원인별 개수(CLARA: 미지원 기능 69, 제어 흐름 불일치 35, ILP 6), 실패 그림(TypeCon) | 부분적(R5의 빈 입력, R3 생성기 범위) |
| 수작업 검사 | 무작위 100개 수리를 범주화(CLARA), 수작업 군집 검토(SemCluster) | 규칙 이름 평가(평가자 3명, κ=0.890) |
| ablation | 거리·정렬 방식(Sarfgen), 특징 조합(SemCluster) | Synthesize, 참조 풀, local-first, Learn |
| 비용·시간 | 시간 위주. 달러는 없음 | 달러 비용이 헤드라인 |

---

## 3. PLDI 관점에서 본 CoEP의 차이

| 축 | SE 학회 원고(현재) | PLDI 기대 |
|---|---|---|
| 기여의 정체 | 비용 상각(21–27배 저렴), 반복 수리 관찰 | **과제별 error model(재작성 규칙 집합)의 합성**과 그 탐색 |
| 선행 연구와의 계보 | Refactory, PyDex 대비 | **AutoGrader(PLDI'13)의 손으로 쓴 error model → CoEP가 합성.** CLARA, Sarfgen, SemCluster 대비 기술적 축 |
| LLM의 지위 | 시스템 구성요소(빌더, fallback) | **신뢰하지 않는 합성기·오라클.** 보장은 "어떤 빌더든" 성립 |
| 성질 | 언급 없음 | 건전성(T⁺ 기준), 단조성(T ⊆ T⁺), 종료성(예산), 최얕음(BFS), 게이트의 비용·커버리지 보존 |
| 실행 예제 | Preliminaries에서 한 번(cAPS lOCK) | Overview에서 모든 단계를 관통 |
| 평가의 구도 | RQ, 통계, 위협 | 추상화가 실제로 작동함을 보이는 측정: 규칙 조합 깊이, 규칙 적용 수, 과제 간 전이, 실패 원인. 통계는 장점으로 유지 |
| 한계 서술 | Threats (1)–(4) | 직접적인 한 문장 인정. 범위를 한정하는 정리 |

---

## 4. 원고 수정 권고

### P1. 반드시 할 것

1. **AutoGrader를 인용하고 계보를 세운다.**
   - 원문 확인: AutoGrader는 error model을 "written in python in terms of the python AST"로 손으로 쓴다.
   - Intro 문장 예: "Singh et al. showed that a small, hand-written error model of rewrite rules repairs most attempts at an assignment; CoEP synthesizes that error model."
2. **기여를 PL 객체로 다시 쓴다.**
   - **Repair-tool synthesis:** 과제마다 재작성 규칙 집합 L과 수용 검사 T⁺를 합성한다. 빌더는 신뢰하지 않는 합성기이고, Synthesize의 3라운드 정제는 반례 유도 루프(CEGIS 형태)다.
   - **Search:** 규칙 조합에 대한 너비 우선 탐색과 hunk 이식을 정식화한다(규칙의 의미 ρ: Prog → 𝒫(Prog)는 이미 원고에 있음). 탐색 공간과 비용(RPS)도 정의한다.
   - **비용:** 헤드라인이 아니라 상각 구조의 결과로 내린다.
3. **성질을 정확히 진술한다(짧은 명제와 증명).** 구현에서 확인할 것을 괄호에 적었다.
   - (a) **건전성:** \tool이 반환하는 모든 패치는 T⁺를 통과한다. 출처(규칙, 이식, fallback, 학습된 규칙)와 빌더에 관계없다.
   - (b) **단조성:** T ⊆ T⁺이므로 T⁺로 수락된 패치는 T로도 수락된다. 증폭은 수락 집합을 줄일 뿐이다.
   - (c) **최얕음:** 규칙 탐색이 반환하는 수리는 예산 안에서 열거된 층 중 가장 얕은 조합이다. 같은 층 안의 순서는 증상 일치 순서다(구현: 층마다 검증하고 첫 통과를 반환. RPS 최소와는 다르다는 점을 명시).
   - (d) **종료성:** 규칙마다 2초 알람, 탐색 3초 예산, 테스트마다 시간 제한이 있으므로 Repair는 항상 종료한다. 예산 때문에 결정성은 부하에 따라 달라질 수 있다는 점을 인정한다.
   - (e) **게이트:** 에스컬레이션은 커버리지를 잃지 않고 RPS를 키우지 않는다(이미 원고에 있음. 명제로 올린다).
   - (f) **불완전성 인정:** 이식은 hunk 3개 이하, 부분집합 300개 이하만 시도하므로 완전하지 않다. 그래서 fallback이 있다.
4. **Overview 절을 새로 쓴다(약 2쪽).**
   - cAPS lOCK을 관통 예제로 쓴다. 군집 → worked pair → 빌더가 쓴 규칙 `slice_case_check_to_equality` → BFS가 그 규칙으로 다른 제출물 108개를 고침 → T⁺의 증폭 입력이 거르는 과적합 패치 한 개 → fallback 사례 한 개.
   - Figure 1(현재 Preliminaries)을 이 절로 옮긴다.
5. **Preliminaries를 형식 모델로 바꾼다.**
   - 과제 (d, T, B, R), ⊨, 수리의 정의는 유지한다.
   - "Limitation" 절의 측정(Table 1)은 Intro나 Overview로 줄인다.

### P2. 하는 것이 좋을 것

6. **군집화를 구현 세부로 내린다.** 편집 스크립트와 TF-IDF는 휴리스틱이다. SemCluster(PLDI'19)가 "문법 기반 군집화는 과분할한다"고 주장했으므로, 왜 프로그램이 아니라 **편집을** 군집화하는지 한 문단으로 반박한다.
   - 공유하는 정답 부분의 문법 차이는 상쇄된다.
   - 소비자인 재작성 규칙이 문법적이다.
   - 반례 쌍을 하나 든다.
7. **CLARA·Sarfgen과의 기술적 대비를 Intro나 Related에 쓴다.**
   - CLARA: 같은 제어 흐름을 요구하는 것을 스스로 "the only fundamental problem"이라 했다 → CoEP의 hunk 이식은 제어 흐름 일치를 요구하지 않는다. 주장하려면 셀 수 있는 근거가 필요하다.
   - Sarfgen: 정확한 제어 흐름 일치, 수정 3개 상한, 과적합 방지 없음.
8. **평가를 PLDI식 측정으로 보강한다.** 기존 데이터로 대부분 가능하다.
   - 규칙 조합 깊이 히스토그램
   - 수리에 쓰인 규칙 수
   - 과제 간 규칙 전이(1/128)
   - 실패 원인별 개수
   - (새 작업) CLARA식 무작위 100개 수리 수작업 범주화
9. **Related Work를 보강한다.**
   - 추가할 것: AutoGrader, Qlose, Rivers & Koedinger, Head et al.(군집에서 변환 학습), CEGIS/Sketch, TypeCon 같은 LLM과 PL의 결합 연구
   - CCS 개념에 PL 항목을 추가한다(이미 "General programming languages"는 넣음).
10. **한계는 직접적인 한 문장으로 쓴다.** 예: "\tool guarantees correctness only with respect to T⁺."

### P3. 여력이 있으면

11. 증폭의 형식 정의를 추가한다(T⁺ = T ∪ {(x, maj{r(x) | r ∈ R'})}, 90% 합의가 없으면 버림)와 정답이 다수일 때의 정확성 명제.
12. 부록: 프롬프트 전문, 규칙 목록, 사례 연구.

### 분량 배치 제안 (20쪽)

| 절 | 쪽 |
|---|---|
| Intro | 2 |
| Overview(관통 예제) | 2 |
| 형식 모델과 문제 정의 | 1.5 |
| CoEP(Select / Synthesize + Amplify / Repair / Learn, 명제 포함) | 5 |
| 구현 | 0.5 |
| 평가 | 6.5 |
| 한계 | 0.5 |
| 관련 연구 | 1.5 |
| 결론 | 0.3 |
| AI Use | 0.2 |
