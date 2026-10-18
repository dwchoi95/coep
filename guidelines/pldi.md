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

---

## 5. 블라인드 보정 리뷰와 A등급 논문 대비 격차 (2026-10-15)

### 5.1 방법
- PLDI 2026 채택 논문 4편(SAIL, TreeCoder, Expecto, Trace-Guided Synthesis of Effectful Test Generators = Clouseau)과 CoEP를 같은 방식으로 텍스트화하고 익명화했다. 저자·소속·학회·URL·참고문헌·부록을 지우고 A–E로 섞었다.
- 리뷰어 3명이 다섯 편을 모두 읽었다. 전문 분야는 합성·형식기법, 수리·실증 평가, ML for code이고, 읽는 순서는 서로 다르다.
- 한계:
  - 세 리뷰어 모두 작업 디렉터리 이름으로 E가 의뢰자 논문임을 알아챘다.
  - 탈락 논문이 비교군에 없다.
  - 그림 없이 텍스트만 읽혔다.

### 5.2 결과 (A=Strong Accept … D=Strong Reject)
| 논문 | R1 | R2 | R3 | 순위 |
|---|---|---|---|---|
| Clouseau (채택) | A | A | A | 1/1/1 |
| CoEP | C | C | C | 2/2/3 |
| Expecto (채택) | C | C | B | 3/3/2 |
| SAIL (채택) | D | C | C | 4/4/4 |
| TreeCoder (채택) | D | D | D | 5/5/5 |

CoEP 세부 평균(5점 만점):
- 평가 3.0, 명료성 3.7 → 채택 논문과 같거나 높음
- PL 깊이 2.3, 의의 2.3, 적합성 2.3 → 하위권

### 5.3 Clouseau(A)의 구조
- 쪽 배분:
  - 서론 2.5쪽 (1쪽에 판단식 `⊢ e : [H] t [F]`)
  - 개요 5쪽 (세 도메인 × 명세 → 합성 코드 → 약한 명세)
  - 형식화 5쪽 (계산체계, 의미론, 타이핑 규칙, 정리 2개)
  - 합성 3.5쪽 (알고리즘 각 줄이 타이핑 규칙에 대응, Thm 4.4 건전성)
  - 평가 4.5쪽 (약 20%)
  - 관련 연구와 결론 1쪽
- 기여 서술 순서: 새 타입 추상화 → 타입 붙은 DSL → 타입 기반 합성 절차와 평가. 도구는 결과물로 나온다.
- 관통 예제 하나(stack)가 Ex 3.1 → 3.2 → 4.1 → 4.2 → 4.3으로 이어진다.
- 설계 선택을 반사실로 정당화한다(각주 1: 과근사 해석은 말이 안 된다).
- 이론 계보를 명시한다(IL의 trace 버전, HAT의 과소근사 버전).
- 보장의 전제를 정의로 못 박는다(Def 3.3).
- 개요의 약한 명세 예제가 Q4 강건성 실험이 된다.
- 평가는 오히려 약하다(평균만, 분산 없음, 랜덤 베이스라인). 그래도 리뷰어 셋이 모두 A를 줬다. **PLDI는 PL 기여가 결과를 실제로 떠받치는지를 통계적 엄밀성보다 무겁게 본다.**

### 5.4 CoEP의 격차
| 축 | CoEP 현재 | 심각도 |
|---|---|---|
| 중심 PL 객체 | 규칙이 임의의 Python이고 의미론이 없음 | 치명 |
| 결과를 떠받치는 요소 | 이름에 걸린 합성 규칙의 커버리지 기여 +0.18%p | 치명 |
| 형식화와 알고리즘 연결 | 명제가 구성에서 바로 따라나옴 | 높음 |
| 쪽 배분 | 평가 약 40%, 형식 약 6% | 높음 |
| 관통 예제 | cAPS lOCK이 개요에서 끝남 | 중간 |
| 이론 계보 | Singh et al. 한 줄, Refazer와의 차별 약함 | 중간 |

### 5.5 로그만으로 재구성한 2×2 ablation (`run.py ablation` → results/ablation.csv)
LLM_Direct는 CoEP_LF가 에스컬레이션할 때 보내는 질의와 같은 질의를 모든 프로그램에 보낸 팔이다. 그래서 "로컬 도구 + 같은 게이트 + Direct 응답"으로 새 API 호출 없이 팔을 재구성했다. 재구성한 full은 실측 CoEP_LF와 쌍 단위로 99.93% 일치한다.

| 팔 (claude-sonnet-5 / gpt-5.4-mini) | RR(T) | held-out RR | RPS | RR_0.25 | 총비용($) |
|---|---|---|---|---|---|
| full (규칙 + T⁺) | 99.33 / 99.46 | 99.13 / 98.96 | 0.417 / 0.440 | 43.0 / 40.1 | 13.81 / 1.04 |
| −rules | 99.26 / 99.46 | 99.06 / 98.96 | 0.446 / 0.456 | 36.6 / 36.5 | **1.69 / 0.36** |
| −amp | 99.66 / 99.76 | **94.11 / 92.83** | 0.401 / 0.421 | 41.4 / 37.6 | 13.71 / 1.00 |
| −rules −amp | 99.53 / 99.66 | 93.84 / 93.97 | 0.429 / 0.439 | 35.0 / 35.1 | 1.60 / 0.33 |
| PyDex | 98.96 / 98.92 | 97.64 / 97.71 | 0.598 / 0.669 | 37.0 / 24.1 | 292.77 / 28.42 |

해석:
1. **비용 이점은 규칙이 아니라 local-first 구조(이식 + 게이트)에서 나온다.** −rules도 PyDex보다 173배(cs), 79배(gm) 싸다.
2. **증폭 생성기는 $0.02/$0.01로 held-out 수리율을 +5.0/+6.1%p 올린다.** LLM이 합성한 것 중 결과를 가장 크게 떠받친다.
3. **합성 규칙은 커버리지가 아니라 패치 최소성을 산다.**
   - RR_0.25: +6.4%p / +3.6%p. 규칙이 있어야만 작은 패치가 되는 경우 193개·107개, 반대 경우 5개·0개 (빌더별 McNemar p < 1e-30)
   - 공통 수리의 RPS: 0.418 대 0.447 (cs), 0.441 대 0.457 (gm) (Wilcoxon p < 1e-26)
   - 참조 0개일 때 커버리지 8.2% → 30.1% (Table 4)
4. 규칙 수리 1,293개의 구성: 합성 규칙만 827개, 범용 규칙만 326개, 혼합 140개. 합성 규칙이 관여한 수리는 967개(74.8%)다.

### 5.6 보완 목록 (리뷰 지적 + Clouseau 대비)
- **A. 기여 재정의:** 수리 도구 = (재작성 규칙, 이식, 수용 오라클 T⁺). LLM이 과제마다 만드는 것은 규칙과 오라클 생성기다. 비용 이점은 local-first 구조, 정확성은 합성된 오라클, 패치 최소성은 합성된 규칙에 귀속한다. 제목과 기여 문장을 이 귀속에 맞춘다.
- **B. 형식화:**
  - 규칙 계약(가드 + 소스 구간 치환)을 작은 규칙 언어로 정의하고, 조합 깊이 j에 대한 패치 크기 상한을 증명한다.
  - 증폭의 정의와 레이블 정확성 명제를 쓰고, 그 전제를 정의로 둔다.
  - 신뢰 경계를 명세한다.
  - 알고리즘 각 줄이 어느 명제를 성립시키는지 표시한다.
- **C. 서술:**
  - cAPS lOCK을 §4 끝까지 관통시킨다.
  - 서론 1쪽에 형식 객체를 둔다.
  - 핵심 설계 선택을 반사실로 정당화한다.
  - 계보를 정리한다(Singh et al. error model 합성, Refazer와의 차이).
- **D. 평가:**
  - 약 8.3쪽에서 약 5.5쪽으로 줄이고 세부는 부록으로 옮긴다.
  - 같은 조건의 베이스라인을 둔다(T⁺ 수용, 후보 수 곡선).
  - 빌더별 통계로 바꾼다.
  - RPS ≥ 1 수리 수를 보고한다.
  - 도구 특성 표를 넣는다.
  - 오라클 충돌을 분석한다.
- **E. 텍스트 정정:**
  - Algorithm 1 RPS 게이트
  - Learn 조건의 명칭
  - §4.4 과장
  - 배포 단계 데이터 유출 범위
  - $0.89 포함 여부
  - Fig 1(b) 주석
  - top_k([], 0) 절차 (실험 필요)
- **F. AI Use 절** (CFP 요건)

### 5.7 3차 블라인드 리뷰 (2026-10-16, 계약 강제·재실행 후, 가명 Forge)
| 리뷰어 | E(CoEP) | B(Clouseau) | E 순위 |
|---|---|---|---|
| 1 합성·형식 | C | B | 2/5 |
| 2 수리·실험 | C | A | 3/5 |
| 3 ML4code | C | A | 2/5 |

나머지 논문: SAIL D/C/D, Expecto C/C/C, TreeCoder D/D/D.

E 평균 점수 (2차 → 3차):
- 깊이 2.3 → 3.0
- 평가 3.7 → 4.0
- 적합성 2.3 → 2.7
- 참신성 3.0, 중요성 2.7, 명료성 3.0

**Clouseau 대비 후속 질문(세 리뷰어 공통 결론).** 격차는 평가가 아니라 기여의 위치에 있다. 세 리뷰어 모두 E의 평가가 B보다 엄밀하다고 답했다. 근거는 빌더별 정확 검정, 구성 요소 귀속, PyDex에 T⁺ 제공, 정리 4.3 예측의 검증, 재현성이다.

부족한 것 (결정적인 순서):
1. **합성 규칙이 헤드라인 주장을 만든다는 증거.** Table 4에서 −Rules는 5,940쌍 중 2쌍만 바꾸고 비용은 약 8배다. 세 리뷰어 모두 (b)로 분류했고, 그런 구간이 없으면 (c)라고 했다.
2. **정적 지역성과 조합 의미론을 갖춘 규칙 DSL.** 리뷰어 1·3은 B로 올리는 데 필수, 리뷰어 2는 1이 성립하면 선택이라고 했다.
3. **증거와 맞는 프레이밍** (a). 필요하지만 충분하지 않다.
4. **기타:**
   - 클래스와 독립된 오라클(경계값·명세 기반 집합, 참조만으로 재라벨)
   - cluster-then-query-once 베이스라인
   - 블록 이식 대 hunk 이식
   - Refazer 비교
   - 벽시계 예산 대신 노드 예산, |C_k(b)| 분포
   - 상위 난이도 구간 확대
   - 강사 평가

**0원 데이터 확인 (기존 로그).**
- 분할(cold start, f=10–75%): 규칙이 L의 커버리지를 0.5pp 이하로 올리고, 에스컬레이션을 1,317건 중 최대 11건 줄인다. 결정적이지 않다.
- 풀 제한(146개 × 3시드):

  | 정답 프로그램 수 k | 에스컬레이션 (전체 → −Syn) | p | RR_0.25 (전체 → −Syn) | p |
  |---|---|---|---|---|
  | 0 | 71.9% → 91.8% | — | — | — |
  | 1 | 33.1% → 37.9% | 6e-6 | 24.2% → 13.5% | 1e-14 |
  | 2 | 21.2% → 23.7% | 0.013 | — | — |
  | 5 | 차이 없음 | — | — | — |

- 결론: 현실적인 풀에서 커버리지가 결정적으로 달라지는 구간은 없다. 빈약한 풀(새 과제)에서는 규칙이 에스컬레이션과 패치 크기를 유의하게 줄인다.

### 5.8 경로 1 결과 (2026-10-18, 3차 리뷰 대응)

API 비용은 재빌드 약 $31뿐이다. 나머지는 모두 로컬 재실행이다.

- **탐색 예산.** 3초 시간 예산을 노드 예산(η_search = 1,000개 후보)으로 바꾸고, 시간 제한을 넘긴 후보는 더 확장하지 않는다.
  - 기존 방식에서는 규칙 탐색의 58%가 시간 예산에서 끊겼다.
  - 전체 재실행에서 패치 5,940개가 100% 그대로 재현됐다.
  - |C(b)| ≤ 1,300이므로 정리 4.3의 상한은 R1–R5의 모든 수리에서 3.5% 미만이다(중앙값 2.7%).
  - 처리 시간: CPU 3.92/4.61초, 합계 4.29/4.75초(이전 3.02/3.21초). 중앙값은 오히려 1.5–1.8초로 빨라졌고, 꼬리가 길어졌다.
- **증폭 절차 수정.** T_amp가 held-out 입력을 피하던 의존을 제거했다(배포 시점에는 평가 집합이 없다). held-out과 경계값 집합이 두 빌더의 T⁺를 피한다.
  - R5의 `top_k([], 0)` 실패 6건이 사라졌다.
  - 레이블 1,500개가 모두 참조 해답과 일치한다.
- **held-out.**
  - CoEP_LF 98.9/98.6 대 PyDex 96.4/97.2 (p<0.001, 0.005).
  - T만으로 받아들이면 90.4/90.4.
  - 같은 T⁺를 준 PyDex: cs 97.3 (p<0.001로 CoEP 우위), gm 99.0 (p=0.27, 동률).
- **경계값 집합(신규).** 문제 설명에서 손으로 쓴 경계 입력을 참조 해답으로 라벨링했다.
  - CoEP_LF 98.5/99.1 대 PyDex 94.7/97.1 (p<0.001), T만 87.9/88.0.
  - PyDex+T⁺는 97.1/99.0.
- **새 과제 실험.** f10 도구, 정답 k∈{1,2,5}, 빌더당 1,630개.
  - 규칙은 에스컬레이션을 cs 28.8→24.6%(k=1, 69:0)로 줄이고, RR_0.25를 2.1–4.8pt 올린다.
  - 커버리지는 99.1–99.8%로 차이가 없다. "규칙이 커버리지를 좌우하는 현실적 구간은 없다"가 결론이다.
- **재빌드 분산.** 빌드 3회 기준이다.
  - RR 변동 ≤0.07pt, held-out ≤0.3pt, RPS ≤0.009, RR_0.25 ≤2.5pt.
  - 비용 cs $13.83–16.57, gm $1.04–1.24 (PyDex 대비 ≥18×, ≥23×).
  - 규칙 수 cs 152–175, gm 132–146.
- **변하지 않은 헤드라인.** 99.4%, 21.2×/27.3×, 31% 작은 패치, Learn 15개, 분할 99.3/98.9.
- **남은 리뷰 지적.**
  - 규칙 DSL(경로 2)
  - 클러스터당 1회 질의 베이스라인
  - 블록 대 hunk 이식 비교
  - 상위 난이도 구간 확대
