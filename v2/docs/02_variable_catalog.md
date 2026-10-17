# 변수 파악 (2단계)

연체 위험 기반 대출 승인 기준 설계 (Loan Approval Risk Scoring) — v2 재분석

데이터 출처: Home Credit Default Risk (Kaggle, 해외 소비자금융사 공개 대출 데이터)

> 이 문서는 TARGET(연체 여부)과 변수 사이의 관계를 계산하지 않는다. 각 변수의 자료형, 결측률, 분포만 기록한다. 가설은 이 문서를 본 뒤 다음 단계에서 세운다.

재현 코드: [`v2/scripts/02_variable_catalog.py`](../scripts/02_variable_catalog.py)

---

## 2-1. application_train 변수 카탈로그 (122개 전부)

컬럼 설명은 Kaggle 제공 `HomeCredit_columns_description.csv`의 영문 원문을 기반으로 한다(인코딩 cp1252로 읽음). "대표 분포"는 숫자형이면 `min / 중앙값(med) / max`, 범주형이면 상위 3개 범주와 건수다.

업무 의미별 분류와 변수 수:

| 분류 | 변수 수 |
|---|---|
| 식별자 | 1 |
| 타겟 | 1 |
| 대출 조건 | 4 |
| 인적 사항 | 4 |
| 소득·재산 | 4 |
| 가족 | 4 |
| 고용·직업 | 5 |
| 거주지·지역 | 10 |
| 주택 건물 정보 | 47 |
| 연락처·서류 제출 여부 | 27 |
| 외부 신용점수 | 3 |
| 신용조회 이력 | 6 |
| 주변인 연체 관측 | 4 |
| 신청 시점 | 2 |
| **합계** | **122** |

"주택 건물 정보"(47개)와 "연락처·서류 제출 여부"(27개)가 전체의 60%를 차지한다. 주택 건물 정보는 아파트 면적·엘리베이터·건축연한 등을 평균(_AVG)/최빈값(_MODE)/중앙값(_MEDI) 세 가지 방식으로 중복 기록한 것이라 실질 정보량은 더 적다(동일 항목 x3).

### 식별자 (1개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| SK_ID_CURR | ID of loan in our sample | BIGINT | 0.0% | 307,511 | min 100,002 / med 278,202 / max 456,255 |

### 타겟 (1개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| TARGET | Target variable (1 - client with payment difficulties: he/she had l... | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |

### 대출 조건 (4개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| NAME_CONTRACT_TYPE | Identification if loan is cash or revolving | VARCHAR | 0.0% | 2 | Cash loans(278,232), Revolving loans(29,279) |
| AMT_CREDIT | Credit amount of the loan | DOUBLE | 0.0% | 5,603 | min 45,000 / med 513,531 / max 4,050,000 |
| AMT_ANNUITY | Loan annuity | DOUBLE | 0.004% | 13,672 | min 1,615.5 / med 24,903 / max 258,025.5 |
| AMT_GOODS_PRICE | For consumer loans it is the price of the goods for which the loan ... | DOUBLE | 0.09% | 1,002 | min 40,500 / med 450,000 / max 4,050,000 |

### 인적 사항 (4개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| CODE_GENDER | Gender of the client | VARCHAR | 0.0% | 3 | F(202,448), M(105,059), XNA(4) |
| DAYS_BIRTH | Client's age in days at the time of application | BIGINT | 0.0% | 17,460 | min -25,229 / med -15,750 / max -7,489 |
| DAYS_REGISTRATION | How many days before the application did client change his registra... | DOUBLE | 0.0% | 15,688 | min -24,672 / med -4,504 / max 0 |
| DAYS_ID_PUBLISH | How many days before the application did client change the identity... | BIGINT | 0.0% | 6,168 | min -7,197 / med -3,254 / max 0 |

### 소득·재산 (4개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| FLAG_OWN_CAR | Flag if the client owns a car | VARCHAR | 0.0% | 2 | N(202,924), Y(104,587) |
| FLAG_OWN_REALTY | Flag if client owns a house or flat | VARCHAR | 0.0% | 2 | Y(213,312), N(94,199) |
| AMT_INCOME_TOTAL | Income of the client | DOUBLE | 0.0% | 2,548 | min 25,650 / med 147,150 / max 117,000,000 |
| OWN_CAR_AGE | Age of client's car | DOUBLE | 65.991% | 62 | min 0 / med 9 / max 91 |

### 가족 (4개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| CNT_CHILDREN | Number of children the client has | BIGINT | 0.0% | 15 | min 0 / med 0 / max 19 |
| NAME_TYPE_SUITE | Who was accompanying client when he was applying for the loan | VARCHAR | 0.42% | 7 | Unaccompanied(248,526), Family(40,149), Spouse, partner(11,370) |
| NAME_FAMILY_STATUS | Family status of the client | VARCHAR | 0.0% | 6 | Married(196,432), Single / not married(45,444), Civil marriage(29,775) |
| CNT_FAM_MEMBERS | How many family members does client have | DOUBLE | 0.001% | 17 | min 1 / med 2 / max 20 |

### 고용·직업 (5개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| NAME_INCOME_TYPE | Clients income type (businessman, working, maternity leave,…) | VARCHAR | 0.0% | 8 | Working(158,774), Commercial associate(71,617), Pensioner(55,362) |
| NAME_EDUCATION_TYPE | Level of highest education the client achieved | VARCHAR | 0.0% | 5 | Secondary / secondary special(218,391), Higher education(74,863), Incomplete higher(10,277) |
| DAYS_EMPLOYED | How many days before the application the person started current emp... | BIGINT | 0.0% | 12,574 | min -17,912 / med -1,213 / max 365,243 |
| OCCUPATION_TYPE | What kind of occupation does the client have | VARCHAR | 31.346% | 18 | None(96,391), Laborers(55,186), Sales staff(32,102) |
| ORGANIZATION_TYPE | Type of organization where client works | VARCHAR | 0.0% | 58 | Business Entity Type 3(67,992), XNA(55,374), Self-employed(38,412) |

### 거주지·지역 (10개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| NAME_HOUSING_TYPE | What is the housing situation of the client (renting, living with p... | VARCHAR | 0.0% | 6 | House / apartment(272,868), With parents(14,840), Municipal apartment(11,183) |
| REGION_POPULATION_RELATIVE | Normalized population of region where client lives (higher number m... | DOUBLE | 0.0% | 81 | min 0 / med 0.02 / max 0.07 |
| REGION_RATING_CLIENT | Our rating of the region where client lives (1,2,3) | BIGINT | 0.0% | 3 | min 1 / med 2 / max 3 |
| REGION_RATING_CLIENT_W_CITY | Our rating of the region where client lives with taking city into a... | BIGINT | 0.0% | 3 | min 1 / med 2 / max 3 |
| REG_REGION_NOT_LIVE_REGION | Flag if client's permanent address does not match contact address (... | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| REG_REGION_NOT_WORK_REGION | Flag if client's permanent address does not match work address (1=d... | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| LIVE_REGION_NOT_WORK_REGION | Flag if client's contact address does not match work address (1=dif... | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| REG_CITY_NOT_LIVE_CITY | Flag if client's permanent address does not match contact address (... | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| REG_CITY_NOT_WORK_CITY | Flag if client's permanent address does not match work address (1=d... | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| LIVE_CITY_NOT_WORK_CITY | Flag if client's contact address does not match work address (1=dif... | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |

### 주택 건물 정보 (47개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| APARTMENTS_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 50.75% | 2,339 | min 0 / med 0.09 / max 1 |
| BASEMENTAREA_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 58.516% | 3,780 | min 0 / med 0.08 / max 1 |
| YEARS_BEGINEXPLUATATION_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 48.781% | 285 | min 0 / med 0.98 / max 1 |
| YEARS_BUILD_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 66.498% | 149 | min 0 / med 0.76 / max 1 |
| COMMONAREA_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 69.872% | 3,181 | min 0 / med 0.02 / max 1 |
| ELEVATORS_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 53.296% | 257 | min 0 / med 0 / max 1 |
| ENTRANCES_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 50.349% | 285 | min 0 / med 0.14 / max 1 |
| FLOORSMAX_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 49.761% | 403 | min 0 / med 0.17 / max 1 |
| FLOORSMIN_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 67.849% | 305 | min 0 / med 0.21 / max 1 |
| LANDAREA_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 59.377% | 3,527 | min 0 / med 0.05 / max 1 |
| LIVINGAPARTMENTS_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 68.355% | 1,868 | min 0 / med 0.08 / max 1 |
| LIVINGAREA_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 50.193% | 5,199 | min 0 / med 0.07 / max 1 |
| NONLIVINGAPARTMENTS_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 69.433% | 386 | min 0 / med 0 / max 1 |
| NONLIVINGAREA_AVG | Normalized information about building where the client lives, What ... | DOUBLE | 55.179% | 3,290 | min 0 / med 0 / max 1 |
| APARTMENTS_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 50.75% | 760 | min 0 / med 0.08 / max 1 |
| BASEMENTAREA_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 58.516% | 3,841 | min 0 / med 0.07 / max 1 |
| YEARS_BEGINEXPLUATATION_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 48.781% | 221 | min 0 / med 0.98 / max 1 |
| YEARS_BUILD_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 66.498% | 154 | min 0 / med 0.76 / max 1 |
| COMMONAREA_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 69.872% | 3,128 | min 0 / med 0.02 / max 1 |
| ELEVATORS_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 53.296% | 26 | min 0 / med 0 / max 1 |
| ENTRANCES_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 50.349% | 30 | min 0 / med 0.14 / max 1 |
| FLOORSMAX_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 49.761% | 25 | min 0 / med 0.17 / max 1 |
| FLOORSMIN_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 67.849% | 25 | min 0 / med 0.21 / max 1 |
| LANDAREA_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 59.377% | 3,563 | min 0 / med 0.05 / max 1 |
| LIVINGAPARTMENTS_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 68.355% | 736 | min 0 / med 0.08 / max 1 |
| LIVINGAREA_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 50.193% | 5,301 | min 0 / med 0.07 / max 1 |
| NONLIVINGAPARTMENTS_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 69.433% | 167 | min 0 / med 0 / max 1 |
| NONLIVINGAREA_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 55.179% | 3,327 | min 0 / med 0 / max 1 |
| APARTMENTS_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 50.75% | 1,148 | min 0 / med 0.09 / max 1 |
| BASEMENTAREA_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 58.516% | 3,772 | min 0 / med 0.08 / max 1 |
| YEARS_BEGINEXPLUATATION_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 48.781% | 245 | min 0 / med 0.98 / max 1 |
| YEARS_BUILD_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 66.498% | 151 | min 0 / med 0.76 / max 1 |
| COMMONAREA_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 69.872% | 3,202 | min 0 / med 0.02 / max 1 |
| ELEVATORS_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 53.296% | 46 | min 0 / med 0 / max 1 |
| ENTRANCES_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 50.349% | 46 | min 0 / med 0.14 / max 1 |
| FLOORSMAX_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 49.761% | 49 | min 0 / med 0.17 / max 1 |
| FLOORSMIN_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 67.849% | 47 | min 0 / med 0.21 / max 1 |
| LANDAREA_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 59.377% | 3,560 | min 0 / med 0.05 / max 1 |
| LIVINGAPARTMENTS_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 68.355% | 1,097 | min 0 / med 0.08 / max 1 |
| LIVINGAREA_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 50.193% | 5,281 | min 0 / med 0.07 / max 1 |
| NONLIVINGAPARTMENTS_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 69.433% | 214 | min 0 / med 0 / max 1 |
| NONLIVINGAREA_MEDI | Normalized information about building where the client lives, What ... | DOUBLE | 55.179% | 3,323 | min 0 / med 0 / max 1 |
| FONDKAPREMONT_MODE | Normalized information about building where the client lives, What ... | VARCHAR | 68.386% | 4 | None(210,295), reg oper account(73,830), reg oper spec account(12,080) |
| HOUSETYPE_MODE | Normalized information about building where the client lives, What ... | VARCHAR | 50.176% | 3 | None(154,297), block of flats(150,503), specific housing(1,499) |
| TOTALAREA_MODE | Normalized information about building where the client lives, What ... | DOUBLE | 48.269% | 5,116 | min 0 / med 0.07 / max 1 |
| WALLSMATERIAL_MODE | Normalized information about building where the client lives, What ... | VARCHAR | 50.841% | 7 | None(156,341), Panel(66,040), Stone, brick(64,815) |
| EMERGENCYSTATE_MODE | Normalized information about building where the client lives, What ... | BOOLEAN | 47.398% | 2 | False(159,428), None(145,755), True(2,328) |

### 연락처·서류 제출 여부 (27개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| FLAG_MOBIL | Did client provide mobile phone (1=YES, 0=NO) | BIGINT | 0.0% | 2 | min 0 / med 1 / max 1 |
| FLAG_EMP_PHONE | Did client provide work phone (1=YES, 0=NO) | BIGINT | 0.0% | 2 | min 0 / med 1 / max 1 |
| FLAG_WORK_PHONE | Did client provide home phone (1=YES, 0=NO) | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_CONT_MOBILE | Was mobile phone reachable (1=YES, 0=NO) | BIGINT | 0.0% | 2 | min 0 / med 1 / max 1 |
| FLAG_PHONE | Did client provide home phone (1=YES, 0=NO) | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_EMAIL | Did client provide email (1=YES, 0=NO) | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| DAYS_LAST_PHONE_CHANGE | How many days before application did client change phone | DOUBLE | 0.0% | 3,773 | min -4,292 / med -757 / max 0 |
| FLAG_DOCUMENT_2 | Did client provide document 2 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_3 | Did client provide document 3 | BIGINT | 0.0% | 2 | min 0 / med 1 / max 1 |
| FLAG_DOCUMENT_4 | Did client provide document 4 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_5 | Did client provide document 5 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_6 | Did client provide document 6 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_7 | Did client provide document 7 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_8 | Did client provide document 8 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_9 | Did client provide document 9 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_10 | Did client provide document 10 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_11 | Did client provide document 11 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_12 | Did client provide document 12 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_13 | Did client provide document 13 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_14 | Did client provide document 14 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_15 | Did client provide document 15 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_16 | Did client provide document 16 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_17 | Did client provide document 17 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_18 | Did client provide document 18 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_19 | Did client provide document 19 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_20 | Did client provide document 20 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |
| FLAG_DOCUMENT_21 | Did client provide document 21 | BIGINT | 0.0% | 2 | min 0 / med 0 / max 1 |

### 외부 신용점수 (3개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| EXT_SOURCE_1 | Normalized score from external data source | DOUBLE | 56.381% | 114,584 | min 0.01 / med 0.51 / max 0.96 |
| EXT_SOURCE_2 | Normalized score from external data source | DOUBLE | 0.215% | 119,831 | min 0 / med 0.57 / max 0.85 |
| EXT_SOURCE_3 | Normalized score from external data source | DOUBLE | 19.825% | 814 | min 0 / med 0.54 / max 0.9 |

### 신용조회 이력 (6개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| AMT_REQ_CREDIT_BUREAU_HOUR | Number of enquiries to Credit Bureau about the client one hour befo... | DOUBLE | 13.502% | 5 | min 0 / med 0 / max 4 |
| AMT_REQ_CREDIT_BUREAU_DAY | Number of enquiries to Credit Bureau about the client one day befor... | DOUBLE | 13.502% | 9 | min 0 / med 0 / max 9 |
| AMT_REQ_CREDIT_BUREAU_WEEK | Number of enquiries to Credit Bureau about the client one week befo... | DOUBLE | 13.502% | 9 | min 0 / med 0 / max 8 |
| AMT_REQ_CREDIT_BUREAU_MON | Number of enquiries to Credit Bureau about the client one month bef... | DOUBLE | 13.502% | 24 | min 0 / med 0 / max 27 |
| AMT_REQ_CREDIT_BUREAU_QRT | Number of enquiries to Credit Bureau about the client 3 month befor... | DOUBLE | 13.502% | 11 | min 0 / med 0 / max 261 |
| AMT_REQ_CREDIT_BUREAU_YEAR | Number of enquiries to Credit Bureau about the client one day year ... | DOUBLE | 13.502% | 25 | min 0 / med 1 / max 25 |

### 주변인 연체 관측 (4개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| OBS_30_CNT_SOCIAL_CIRCLE | How many observation of client's social surroundings with observabl... | DOUBLE | 0.332% | 33 | min 0 / med 0 / max 348 |
| DEF_30_CNT_SOCIAL_CIRCLE | How many observation of client's social surroundings defaulted on 3... | DOUBLE | 0.332% | 10 | min 0 / med 0 / max 34 |
| OBS_60_CNT_SOCIAL_CIRCLE | How many observation of client's social surroundings with observabl... | DOUBLE | 0.332% | 33 | min 0 / med 0 / max 344 |
| DEF_60_CNT_SOCIAL_CIRCLE | How many observation of client's social surroundings defaulted on 6... | DOUBLE | 0.332% | 9 | min 0 / med 0 / max 24 |

### 신청 시점 (2개)

| 컬럼명 | 설명(원문 기반) | 자료형 | 결측률 | 고유값 수 | 대표 분포 |
|---|---|---|---|---|---|
| WEEKDAY_APPR_PROCESS_START | On which day of the week did the client apply for the loan | VARCHAR | 0.0% | 7 | TUESDAY(53,901), WEDNESDAY(51,934), MONDAY(50,714) |
| HOUR_APPR_PROCESS_START | Approximately at what hour did the client apply for the loan | BIGINT | 0.0% | 24 | min 0 / med 12 / max 23 |

---

## 2-2. 하위 테이블 요약

### bureau (타 금융기관 신용 정보)

* **담고 있는 정보**: 신청자가 Home Credit 외 다른 금융기관(타 신용정보기관 보고 대상)에 보유한 과거/현재 신용(대출, 카드 등) 내역.
* **행 단위**: 신용 1건 = 1행 (SK_ID_BUREAU 1개당 1행).
* **주요 컬럼**: `SK_ID_CURR`(신청자 연결키), `CREDIT_ACTIVE`(활성/종료 상태), `CREDIT_TYPE`(신용 종류), `DAYS_CREDIT`(신청일 기준 개설일), `DAYS_CREDIT_ENDDATE`(만기일), `AMT_CREDIT_SUM`(신용 총액), `AMT_CREDIT_SUM_DEBT`(현재 채무액), `AMT_CREDIT_SUM_OVERDUE`(연체 총액), `CREDIT_DAY_OVERDUE`(연체일수), `CNT_CREDIT_PROLONG`(연장 횟수).
* **신청자 1명당 기록 수**: 평균 5.61건 / 중앙값 4건 / 최대 116건 (이력 있는 신청자 기준).
* **알 수 있는 행동 예시**: 다른 금융기관에서도 대출/카드를 보유하고 있었는지, 그중 연체가 있었는지, 전체 부채 규모가 얼마인지.

### bureau_balance (타 금융기관 신용의 월별 상태)

* **담고 있는 정보**: bureau의 각 신용에 대한 월별 상태 스냅샷(DPD 구간, 활성 여부).
* **행 단위**: 신용(SK_ID_BUREAU) x 월(MONTHS_BALANCE) = 1행.
* **주요 컬럼**: `SK_ID_BUREAU`(연결키), `MONTHS_BALANCE`(신청일 기준 월, 0 또는 음수), `STATUS`(0=정상, 1~5=연체 구간, C=완료, X=알수없음).
* **신용 1건당 기록 수**: 평균 33.4개월 / 중앙값 26개월 / 최대 97개월.
* **알 수 있는 행동 예시**: 타 금융기관 신용에서 월별로 연체 구간이 어떻게 변화했는지(상환 궤적).

### previous_application (과거 Home Credit 신청)

* **담고 있는 정보**: 신청자의 과거 Home Credit 대출 신청 1건의 조건과 결과(승인/거절/취소).
* **행 단위**: 신청 1건 = 1행 (SK_ID_PREV 1개당 1행).
* **주요 컬럼**: `SK_ID_CURR`(연결키), `NAME_CONTRACT_TYPE`(대출 종류), `AMT_APPLICATION`(신청액), `AMT_CREDIT`(승인액), `NAME_CONTRACT_STATUS`(Approved/Refused/Canceled/Unused offer), `CODE_REJECT_REASON`(거절 이유), `DAYS_DECISION`(심사일), `CNT_PAYMENT`(할부 개월 수), `NAME_YIELD_GROUP`(금리 그룹), `CHANNEL_TYPE`(판매 채널).
* **신청자 1명당 기록 수**: 평균 1.0건(SK_ID_PREV 자체가 테이블의 유일 키이므로 "SK_ID_PREV당 1건"은 항상 1; 신청자당 과거 신청 건수는 이력 보유자 기준 평균 약 5.4건 — `previous_application_to_application` 참고).
* **알 수 있는 행동 예시**: 과거에 몇 번 신청했는지, 거절된 적이 있는지, 거절 이유가 무엇이었는지, 신청액 대비 실제 승인액이 깎였는지.

### POS_CASH_balance (POS/현금대출 월별 상태)

* **담고 있는 정보**: previous_application의 POS(매장 할부)/현금대출에 대한 월별 상태(남은 할부 횟수, 연체일수).
* **행 단위**: 이전 신청(SK_ID_PREV) x 월(MONTHS_BALANCE) = 1행.
* **주요 컬럼**: `SK_ID_PREV`(연결키), `MONTHS_BALANCE`, `CNT_INSTALMENT`(총 할부 횟수), `CNT_INSTALMENT_FUTURE`(남은 할부 횟수), `NAME_CONTRACT_STATUS`(Active/Completed/Signed 등), `SK_DPD`(연체일수), `SK_DPD_DEF`(허용범위 제외 연체일수).
* **이전 신청 1건당 기록 수**: 평균 10.68개월 / 중앙값 10개월 / 최대 96개월.
* **알 수 있는 행동 예시**: 과거 할부 대출을 월별로 어떻게 상환해 왔는지, 연체가 몇 달 지속됐는지.

### installments_payments (분할상환 기록)

* **담고 있는 정보**: previous_application의 분할상환 회차별 예정액/예정일과 실제 납부액/납부일.
* **행 단위**: 이전 신청(SK_ID_PREV) x 할부 회차(NUM_INSTALMENT_NUMBER) = 1행.
* **주요 컬럼**: `SK_ID_PREV`(연결키), `NUM_INSTALMENT_NUMBER`(회차), `DAYS_INSTALMENT`(예정 상환일), `DAYS_ENTRY_PAYMENT`(실제 납부일), `AMT_INSTALMENT`(예정액), `AMT_PAYMENT`(실제 납부액).
* **이전 신청 1건당 기록 수**: 평균 13.64건 / 중앙값 10건 / 최대 293건.
* **알 수 있는 행동 예시**: 정해진 날짜보다 늦게 갚았는지(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT), 예정액보다 적게/많이 갚았는지.

### credit_card_balance (신용카드 월별 잔액)

* **담고 있는 정보**: previous_application의 신용카드 대출에 대한 월별 잔액·한도·결제·인출 내역.
* **행 단위**: 이전 신청(SK_ID_PREV) x 월(MONTHS_BALANCE) = 1행.
* **주요 컬럼**: `SK_ID_PREV`(연결키), `MONTHS_BALANCE`, `AMT_BALANCE`(월말 잔액), `AMT_CREDIT_LIMIT_ACTUAL`(한도), `AMT_DRAWINGS_CURRENT`(인출액), `AMT_PAYMENT_TOTAL_CURRENT`(납부액), `SK_DPD`(연체일수), `CNT_DRAWINGS_CURRENT`(인출 횟수), `NAME_CONTRACT_STATUS`.
* **이전 신청 1건당 기록 수**: 평균 36.82개월 / 중앙값 21개월 / 최대 96개월.
* **알 수 있는 행동 예시**: 카드 한도 대비 사용률, 매월 최소 납부만 했는지 전액 납부했는지, 인출(현금서비스) 빈도.

---

## 2-3. 업무 관점 요약: 대출 심사자가 이 데이터로 알 수 있는 것 / 알 수 없는 것

### 알 수 있는 것

1. **과거 상환 행동** — installments_payments의 예정일 대비 실제 납부일/납부액으로 지연·부족 납부 패턴을 알 수 있다.
2. **타 금융기관 신용 현황과 연체 여부** — bureau/bureau_balance로 외부 신용 보유 규모, 활성 신용 수, DPD 구간별 이력을 알 수 있다.
3. **과거 Home Credit 거절 이력과 이유** — previous_application의 CODE_REJECT_REASON, NAME_CONTRACT_STATUS로 과거 심사 결과를 알 수 있다.
4. **소득·고용 안정성의 자기 보고 정보** — AMT_INCOME_TOTAL, NAME_INCOME_TYPE, DAYS_EMPLOYED, OCCUPATION_TYPE으로 신청 시점의 소득·직업 안정성을 추정할 수 있다.
5. **외부 신용평가 점수** — EXT_SOURCE_1/2/3으로 제3자가 산출한 신용점수를 참고할 수 있다(단, 산출 방식은 비공개).
6. **주변인 연체 관측** — OBS/DEF_30/60_CNT_SOCIAL_CIRCLE로 신청자의 사회적 관계망 내 연체 발생 빈도를 알 수 있다.
7. **거주·가족 안정성 지표** — NAME_HOUSING_TYPE, REG_*_NOT_*_* 주소 불일치 플래그, CNT_FAM_MEMBERS로 거주 안정성을 간접적으로 알 수 있다.

### 알 수 없는 것

1. **이번 대출의 실제 적용 금리** — RATE_INTEREST_PRIMARY/PRIVILEGED는 previous_application에 있지만 결측률 99.6%로 실질적으로 쓸 수 없고, application_train에는 금리 컬럼이 없다.
2. **연체 발생 이후의 회수 금액·회수율** — 연체(TARGET=1) 이후 실제로 얼마를 회수했는지는 어느 테이블에도 없다.
3. **신청자의 실제 지출·소비 패턴** — 신용카드 가맹점 업종, 실생활 지출 항목 등 상세 소비 데이터는 없다.
4. **외부 신용점수(EXT_SOURCE)의 산출 로직과 원천 데이터** — 값만 있고 어떤 기관이, 무엇을 근거로 산출했는지는 비공개다.
5. **신청 이후의 거시경제·고용 상태 변화** — 실업, 소득 변동 등 승인 이후 발생한 외부 충격은 반영되지 않는다.
6. **절대 날짜(연/월/일)** — 모든 시간 변수가 신청일 기준 상대 일수(DAYS_*)뿐이라 특정 연도·계절 효과를 직접 볼 수 없다([01_data_audit.md](01_data_audit.md) 1-6 참고).
7. **공동 신청자·보증인의 개별 신용 정보** — NAME_TYPE_SUITE로 동반인 유형만 알 수 있을 뿐, 동반인/보증인 자체의 신용 데이터는 없다.
