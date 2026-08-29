# 데이터 딕셔너리 (data/raw/ 8개 테이블)

`data/raw/` 원본 CSV를 DuckDB로 직접 스캔해 생성한 컬럼별 통계 요약. 원본 데이터 자체는 GitHub에 포함하지 않으며(§3), 이 문서는 집계 결과만 담는다.

- 카디널리티는 `COUNT(DISTINCT ...)`로 정확히 계산한 값
- median은 `SUMMARIZE`의 q50(근사 분위수) 값
- 범주형 상위 5개 값 비율은 결측치를 제외한 전체 행 대비 비율

## application_train.csv

행 수: 307,511 / 컬럼 수: 122

### 범주형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |
|---|---|---|---|---|---|
| `NAME_CONTRACT_TYPE` | Identification if loan is cash or revolving | VARCHAR | 0.00 | 2 | Cash loans (90.5%); Revolving loans (9.5%) |
| `CODE_GENDER` | Gender of the client | VARCHAR | 0.00 | 3 | F (65.8%); M (34.2%); XNA (0.0%) |
| `FLAG_OWN_CAR` | Flag if the client owns a car | VARCHAR | 0.00 | 2 | N (66.0%); Y (34.0%) |
| `FLAG_OWN_REALTY` | Flag if client owns a house or flat | VARCHAR | 0.00 | 2 | Y (69.4%); N (30.6%) |
| `NAME_TYPE_SUITE` | Who was accompanying client when he was applying for the loan | VARCHAR | 0.42 | 7 | Unaccompanied (80.8%); Family (13.1%); Spouse, partner (3.7%); Children (1.1%); Other_B (0.6%) |
| `NAME_INCOME_TYPE` | Clients income type (businessman, working, maternity leave,…) | VARCHAR | 0.00 | 8 | Working (51.6%); Commercial associate (23.3%); Pensioner (18.0%); State servant (7.1%); Unemployed (0.0%) |
| `NAME_EDUCATION_TYPE` | Level of highest education the client achieved | VARCHAR | 0.00 | 5 | Secondary / secondary special (71.0%); Higher education (24.3%); Incomplete higher (3.3%); Lower secondary (1.2%); Academic degree (0.1%) |
| `NAME_FAMILY_STATUS` | Family status of the client | VARCHAR | 0.00 | 6 | Married (63.9%); Single / not married (14.8%); Civil marriage (9.7%); Separated (6.4%); Widow (5.2%) |
| `NAME_HOUSING_TYPE` | What is the housing situation of the client (renting, living with parents, ...) | VARCHAR | 0.00 | 6 | House / apartment (88.7%); With parents (4.8%); Municipal apartment (3.6%); Rented apartment (1.6%); Office apartment (0.9%) |
| `OCCUPATION_TYPE` | What kind of occupation does the client have | VARCHAR | 31.35 | 18 | Laborers (17.9%); Sales staff (10.4%); Core staff (9.0%); Managers (6.9%); Drivers (6.0%) |
| `WEEKDAY_APPR_PROCESS_START` | On which day of the week did the client apply for the loan | VARCHAR | 0.00 | 7 | TUESDAY (17.5%); WEDNESDAY (16.9%); MONDAY (16.5%); THURSDAY (16.5%); FRIDAY (16.4%) |
| `ORGANIZATION_TYPE` | Type of organization where client works | VARCHAR | 0.00 | 58 | Business Entity Type 3 (22.1%); XNA (18.0%); Self-employed (12.5%); Other (5.4%); Medicine (3.6%) |
| `FONDKAPREMONT_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | VARCHAR | 68.39 | 4 | reg oper account (24.0%); reg oper spec account (3.9%); not specified (1.8%); org spec account (1.8%) |
| `HOUSETYPE_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | VARCHAR | 50.18 | 3 | block of flats (48.9%); specific housing (0.5%); terraced house (0.4%) |
| `WALLSMATERIAL_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | VARCHAR | 50.84 | 7 | Panel (21.5%); Stone, brick (21.1%); Block (3.0%); Wooden (1.7%); Mixed (0.7%) |
| `EMERGENCYSTATE_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | BOOLEAN | 47.40 | 2 | False (51.8%); True (0.8%) |

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_CURR` | ID of loan in our sample | BIGINT | 0.00 | 307511 | 100,002.00 | 456,255.00 | 278,180.52 | 278,221.00 |
| `TARGET` | Target variable (1 - client with payment difficulties: he/she had late payment more than X days on at least one of the first Y installments of the loan in our sample, 0 - all other cases) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.08 | 0.00 |
| `CNT_CHILDREN` | Number of children the client has | BIGINT | 0.00 | 15 | 0.00 | 19.00 | 0.42 | 0.00 |
| `AMT_INCOME_TOTAL` | Income of the client | DOUBLE | 0.00 | 2548 | 25,650.00 | 117,000,000.00 | 168,797.92 | 146,697.38 |
| `AMT_CREDIT` | Credit amount of the loan | DOUBLE | 0.00 | 5603 | 45,000.00 | 4,050,000.00 | 599,026.00 | 513,704.36 |
| `AMT_ANNUITY` | Loan annuity | DOUBLE | 0.00 | 13672 | 1,615.50 | 258,025.50 | 27,108.57 | 24,901.40 |
| `AMT_GOODS_PRICE` | For consumer loans it is the price of the goods for which the loan is given | DOUBLE | 0.09 | 1002 | 40,500.00 | 4,050,000.00 | 538,396.21 | 450,000.04 |
| `REGION_POPULATION_RELATIVE` | Normalized population of region where client lives (higher number means the client lives in more populated region) | DOUBLE | 0.00 | 81 | 0.00 | 0.07 | 0.02 | 0.02 |
| `DAYS_BIRTH` | Client's age in days at the time of application | BIGINT | 0.00 | 17460 | -25,229.00 | -7,489.00 | -16,037.00 | -15,743.00 |
| `DAYS_EMPLOYED` | How many days before the application the person started current employment | BIGINT | 0.00 | 12574 | -17,912.00 | 365,243.00 | 63,815.05 | -1,214.00 |
| `DAYS_REGISTRATION` | How many days before the application did client change his registration | DOUBLE | 0.00 | 15688 | -24,672.00 | 0.00 | -4,986.12 | -4,501.93 |
| `DAYS_ID_PUBLISH` | How many days before the application did client change the identity document with which he applied for the loan | BIGINT | 0.00 | 6168 | -7,197.00 | 0.00 | -2,994.20 | -3,256.00 |
| `OWN_CAR_AGE` | Age of client's car | DOUBLE | 65.99 | 62 | 0.00 | 91.00 | 12.06 | 9.05 |
| `FLAG_MOBIL` | Did client provide mobile phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 1.00 | 1.00 |
| `FLAG_EMP_PHONE` | Did client provide work phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.82 | 1.00 |
| `FLAG_WORK_PHONE` | Did client provide home phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.20 | 0.00 |
| `FLAG_CONT_MOBILE` | Was mobile phone reachable (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 1.00 | 1.00 |
| `FLAG_PHONE` | Did client provide home phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.28 | 0.00 |
| `FLAG_EMAIL` | Did client provide email (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.06 | 0.00 |
| `CNT_FAM_MEMBERS` | How many family members does client have | DOUBLE | 0.00 | 17 | 1.00 | 20.00 | 2.15 | 2.00 |
| `REGION_RATING_CLIENT` | Our rating of the region where client lives (1,2,3) | BIGINT | 0.00 | 3 | 1.00 | 3.00 | 2.05 | 2.00 |
| `REGION_RATING_CLIENT_W_CITY` | Our rating of the region where client lives with taking city into account (1,2,3) | BIGINT | 0.00 | 3 | 1.00 | 3.00 | 2.03 | 2.00 |
| `HOUR_APPR_PROCESS_START` | Approximately at what hour did the client apply for the loan | BIGINT | 0.00 | 24 | 0.00 | 23.00 | 12.06 | 12.00 |
| `REG_REGION_NOT_LIVE_REGION` | Flag if client's permanent address does not match contact address (1=different, 0=same, at region level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.02 | 0.00 |
| `REG_REGION_NOT_WORK_REGION` | Flag if client's permanent address does not match work address (1=different, 0=same, at region level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.05 | 0.00 |
| `LIVE_REGION_NOT_WORK_REGION` | Flag if client's contact address does not match work address (1=different, 0=same, at region level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.04 | 0.00 |
| `REG_CITY_NOT_LIVE_CITY` | Flag if client's permanent address does not match contact address (1=different, 0=same, at city level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.08 | 0.00 |
| `REG_CITY_NOT_WORK_CITY` | Flag if client's permanent address does not match work address (1=different, 0=same, at city level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.23 | 0.00 |
| `LIVE_CITY_NOT_WORK_CITY` | Flag if client's contact address does not match work address (1=different, 0=same, at city level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.18 | 0.00 |
| `EXT_SOURCE_1` | Normalized score from external data source | DOUBLE | 56.38 | 114584 | 0.01 | 0.96 | 0.50 | 0.51 |
| `EXT_SOURCE_2` | Normalized score from external data source | DOUBLE | 0.21 | 119831 | 0.00 | 0.85 | 0.51 | 0.57 |
| `EXT_SOURCE_3` | Normalized score from external data source | DOUBLE | 19.83 | 814 | 0.00 | 0.90 | 0.51 | 0.54 |
| `APARTMENTS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.75 | 2339 | 0.00 | 1.00 | 0.12 | 0.09 |
| `BASEMENTAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 58.52 | 3780 | 0.00 | 1.00 | 0.09 | 0.08 |
| `YEARS_BEGINEXPLUATATION_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.78 | 285 | 0.00 | 1.00 | 0.98 | 0.98 |
| `YEARS_BUILD_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 66.50 | 149 | 0.00 | 1.00 | 0.75 | 0.76 |
| `COMMONAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 69.87 | 3181 | 0.00 | 1.00 | 0.04 | 0.02 |
| `ELEVATORS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 53.30 | 257 | 0.00 | 1.00 | 0.08 | 0.00 |
| `ENTRANCES_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.35 | 285 | 0.00 | 1.00 | 0.15 | 0.14 |
| `FLOORSMAX_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 49.76 | 403 | 0.00 | 1.00 | 0.23 | 0.17 |
| `FLOORSMIN_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 67.85 | 305 | 0.00 | 1.00 | 0.23 | 0.21 |
| `LANDAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 59.38 | 3527 | 0.00 | 1.00 | 0.07 | 0.05 |
| `LIVINGAPARTMENTS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.35 | 1868 | 0.00 | 1.00 | 0.10 | 0.08 |
| `LIVINGAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.19 | 5199 | 0.00 | 1.00 | 0.11 | 0.07 |
| `NONLIVINGAPARTMENTS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 69.43 | 386 | 0.00 | 1.00 | 0.01 | 0.00 |
| `NONLIVINGAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 55.18 | 3290 | 0.00 | 1.00 | 0.03 | 0.00 |
| `APARTMENTS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.75 | 760 | 0.00 | 1.00 | 0.11 | 0.08 |
| `BASEMENTAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 58.52 | 3841 | 0.00 | 1.00 | 0.09 | 0.07 |
| `YEARS_BEGINEXPLUATATION_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.78 | 221 | 0.00 | 1.00 | 0.98 | 0.98 |
| `YEARS_BUILD_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 66.50 | 154 | 0.00 | 1.00 | 0.76 | 0.76 |
| `COMMONAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 69.87 | 3128 | 0.00 | 1.00 | 0.04 | 0.02 |
| `ELEVATORS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 53.30 | 26 | 0.00 | 1.00 | 0.07 | 0.00 |
| `ENTRANCES_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.35 | 30 | 0.00 | 1.00 | 0.15 | 0.14 |
| `FLOORSMAX_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 49.76 | 25 | 0.00 | 1.00 | 0.22 | 0.17 |
| `FLOORSMIN_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 67.85 | 25 | 0.00 | 1.00 | 0.23 | 0.21 |
| `LANDAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 59.38 | 3563 | 0.00 | 1.00 | 0.06 | 0.05 |
| `LIVINGAPARTMENTS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.35 | 736 | 0.00 | 1.00 | 0.11 | 0.08 |
| `LIVINGAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.19 | 5301 | 0.00 | 1.00 | 0.11 | 0.07 |
| `NONLIVINGAPARTMENTS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 69.43 | 167 | 0.00 | 1.00 | 0.01 | 0.00 |
| `NONLIVINGAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 55.18 | 3327 | 0.00 | 1.00 | 0.03 | 0.00 |
| `APARTMENTS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.75 | 1148 | 0.00 | 1.00 | 0.12 | 0.09 |
| `BASEMENTAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 58.52 | 3772 | 0.00 | 1.00 | 0.09 | 0.08 |
| `YEARS_BEGINEXPLUATATION_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.78 | 245 | 0.00 | 1.00 | 0.98 | 0.98 |
| `YEARS_BUILD_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 66.50 | 151 | 0.00 | 1.00 | 0.76 | 0.76 |
| `COMMONAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 69.87 | 3202 | 0.00 | 1.00 | 0.04 | 0.02 |
| `ELEVATORS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 53.30 | 46 | 0.00 | 1.00 | 0.08 | 0.00 |
| `ENTRANCES_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.35 | 46 | 0.00 | 1.00 | 0.15 | 0.14 |
| `FLOORSMAX_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 49.76 | 49 | 0.00 | 1.00 | 0.23 | 0.17 |
| `FLOORSMIN_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 67.85 | 47 | 0.00 | 1.00 | 0.23 | 0.21 |
| `LANDAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 59.38 | 3560 | 0.00 | 1.00 | 0.07 | 0.05 |
| `LIVINGAPARTMENTS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.35 | 1097 | 0.00 | 1.00 | 0.10 | 0.08 |
| `LIVINGAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 50.19 | 5281 | 0.00 | 1.00 | 0.11 | 0.08 |
| `NONLIVINGAPARTMENTS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 69.43 | 214 | 0.00 | 1.00 | 0.01 | 0.00 |
| `NONLIVINGAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 55.18 | 3323 | 0.00 | 1.00 | 0.03 | 0.00 |
| `TOTALAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.27 | 5116 | 0.00 | 1.00 | 0.10 | 0.07 |
| `OBS_30_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings with observable 30 DPD (days past due) default | DOUBLE | 0.33 | 33 | 0.00 | 348.00 | 1.42 | 0.00 |
| `DEF_30_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings defaulted on 30 DPD (days past due) | DOUBLE | 0.33 | 10 | 0.00 | 34.00 | 0.14 | 0.00 |
| `OBS_60_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings with observable 60 DPD (days past due) default | DOUBLE | 0.33 | 33 | 0.00 | 344.00 | 1.41 | 0.00 |
| `DEF_60_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings defaulted on 60 (days past due) DPD | DOUBLE | 0.33 | 9 | 0.00 | 24.00 | 0.10 | 0.00 |
| `DAYS_LAST_PHONE_CHANGE` | How many days before application did client change phone | DOUBLE | 0.00 | 3773 | -4,292.00 | 0.00 | -962.86 | -758.22 |
| `FLAG_DOCUMENT_2` | Did client provide document 2 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_3` | Did client provide document 3 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.71 | 1.00 |
| `FLAG_DOCUMENT_4` | Did client provide document 4 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_5` | Did client provide document 5 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.02 | 0.00 |
| `FLAG_DOCUMENT_6` | Did client provide document 6 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.09 | 0.00 |
| `FLAG_DOCUMENT_7` | Did client provide document 7 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_8` | Did client provide document 8 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.08 | 0.00 |
| `FLAG_DOCUMENT_9` | Did client provide document 9 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_10` | Did client provide document 10 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_11` | Did client provide document 11 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_12` | Did client provide document 12 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_13` | Did client provide document 13 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_14` | Did client provide document 14 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_15` | Did client provide document 15 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_16` | Did client provide document 16 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.01 | 0.00 |
| `FLAG_DOCUMENT_17` | Did client provide document 17 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_18` | Did client provide document 18 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.01 | 0.00 |
| `FLAG_DOCUMENT_19` | Did client provide document 19 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_20` | Did client provide document 20 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_21` | Did client provide document 21 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_HOUR` | Number of enquiries to Credit Bureau about the client one hour before application | DOUBLE | 13.50 | 5 | 0.00 | 4.00 | 0.01 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_DAY` | Number of enquiries to Credit Bureau about the client one day before application (excluding one hour before application) | DOUBLE | 13.50 | 9 | 0.00 | 9.00 | 0.01 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_WEEK` | Number of enquiries to Credit Bureau about the client one week before application (excluding one day before application) | DOUBLE | 13.50 | 9 | 0.00 | 8.00 | 0.03 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_MON` | Number of enquiries to Credit Bureau about the client one month before application (excluding one week before application) | DOUBLE | 13.50 | 24 | 0.00 | 27.00 | 0.27 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_QRT` | Number of enquiries to Credit Bureau about the client 3 month before application (excluding one month before application) | DOUBLE | 13.50 | 11 | 0.00 | 261.00 | 0.27 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_YEAR` | Number of enquiries to Credit Bureau about the client one day year (excluding last 3 months before application) | DOUBLE | 13.50 | 25 | 0.00 | 25.00 | 1.90 | 1.00 |


## application_test.csv

행 수: 48,744 / 컬럼 수: 121

### 범주형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |
|---|---|---|---|---|---|
| `NAME_CONTRACT_TYPE` | Identification if loan is cash or revolving | VARCHAR | 0.00 | 2 | Cash loans (99.1%); Revolving loans (0.9%) |
| `CODE_GENDER` | Gender of the client | VARCHAR | 0.00 | 2 | F (67.0%); M (33.0%) |
| `FLAG_OWN_CAR` | Flag if the client owns a car | VARCHAR | 0.00 | 2 | N (66.3%); Y (33.7%) |
| `FLAG_OWN_REALTY` | Flag if client owns a house or flat | VARCHAR | 0.00 | 2 | Y (69.1%); N (30.9%) |
| `NAME_TYPE_SUITE` | Who was accompanying client when he was applying for the loan | VARCHAR | 1.87 | 7 | Unaccompanied (81.5%); Family (12.1%); Spouse, partner (3.0%); Children (0.8%); Other_B (0.4%) |
| `NAME_INCOME_TYPE` | Clients income type (businessman, working, maternity leave,…) | VARCHAR | 0.00 | 7 | Working (50.3%); Commercial associate (23.4%); Pensioner (19.0%); State servant (7.2%); Student (0.0%) |
| `NAME_EDUCATION_TYPE` | Level of highest education the client achieved | VARCHAR | 0.00 | 5 | Secondary / secondary special (69.7%); Higher education (25.7%); Incomplete higher (3.5%); Lower secondary (1.0%); Academic degree (0.1%) |
| `NAME_FAMILY_STATUS` | Family status of the client | VARCHAR | 0.00 | 5 | Married (66.2%); Single / not married (14.4%); Civil marriage (8.7%); Separated (6.1%); Widow (4.5%) |
| `NAME_HOUSING_TYPE` | What is the housing situation of the client (renting, living with parents, ...) | VARCHAR | 0.00 | 6 | House / apartment (89.5%); With parents (4.6%); Municipal apartment (3.3%); Rented apartment (1.5%); Office apartment (0.8%) |
| `OCCUPATION_TYPE` | What kind of occupation does the client have | VARCHAR | 32.01 | 18 | Laborers (17.8%); Sales staff (10.4%); Core staff (8.9%); Managers (7.3%); Drivers (5.7%) |
| `WEEKDAY_APPR_PROCESS_START` | On which day of the week did the client apply for the loan | VARCHAR | 0.00 | 7 | TUESDAY (20.0%); WEDNESDAY (17.3%); THURSDAY (17.3%); MONDAY (17.2%); FRIDAY (14.9%) |
| `ORGANIZATION_TYPE` | Type of organization where client works | VARCHAR | 0.00 | 58 | Business Entity Type 3 (22.2%); XNA (19.0%); Self-employed (12.1%); Other (5.6%); Medicine (3.5%) |
| `FONDKAPREMONT_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | VARCHAR | 67.28 | 4 | reg oper account (24.9%); reg oper spec account (4.1%); org spec account (1.9%); not specified (1.9%) |
| `HOUSETYPE_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | VARCHAR | 48.46 | 3 | block of flats (50.6%); specific housing (0.5%); terraced house (0.4%) |
| `WALLSMATERIAL_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | VARCHAR | 49.02 | 7 | Panel (23.1%); Stone, brick (21.4%); Block (2.9%); Wooden (1.6%); Mixed (0.7%) |
| `EMERGENCYSTATE_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | BOOLEAN | 45.56 | 2 | False (53.7%); True (0.7%) |

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_CURR` | ID of loan in our sample | BIGINT | 0.00 | 48744 | 100,001.00 | 456,250.00 | 277,796.68 | 278,220.00 |
| `CNT_CHILDREN` | Number of children the client has | BIGINT | 0.00 | 11 | 0.00 | 20.00 | 0.40 | 0.00 |
| `AMT_INCOME_TOTAL` | Income of the client | DOUBLE | 0.00 | 606 | 26,941.50 | 4,410,000.00 | 178,431.81 | 157,500.00 |
| `AMT_CREDIT` | Credit amount of the loan | DOUBLE | 0.00 | 2937 | 45,000.00 | 2,245,500.00 | 516,740.44 | 449,883.57 |
| `AMT_ANNUITY` | Loan annuity | DOUBLE | 0.05 | 7491 | 2,295.00 | 180,576.00 | 29,426.24 | 26,198.36 |
| `AMT_GOODS_PRICE` | For consumer loans it is the price of the goods for which the loan is given | DOUBLE | 0.00 | 677 | 45,000.00 | 2,245,500.00 | 462,618.84 | 395,503.78 |
| `REGION_POPULATION_RELATIVE` | Normalized population of region where client lives (higher number means the client lives in more populated region) | DOUBLE | 0.00 | 81 | 0.00 | 0.07 | 0.02 | 0.02 |
| `DAYS_BIRTH` | Client's age in days at the time of application | BIGINT | 0.00 | 15477 | -25,195.00 | -7,338.00 | -16,068.08 | -15,788.00 |
| `DAYS_EMPLOYED` | How many days before the application the person started current employment | BIGINT | 0.00 | 7863 | -17,463.00 | 365,243.00 | 67,485.37 | -1,292.00 |
| `DAYS_REGISTRATION` | How many days before the application did client change his registration | DOUBLE | 0.00 | 12618 | -23,722.00 | 0.00 | -4,967.65 | -4,480.68 |
| `DAYS_ID_PUBLISH` | How many days before the application did client change the identity document with which he applied for the loan | BIGINT | 0.00 | 5880 | -6,348.00 | 0.00 | -3,051.71 | -3,238.00 |
| `OWN_CAR_AGE` | Age of client's car | DOUBLE | 66.29 | 52 | 0.00 | 74.00 | 11.79 | 9.00 |
| `FLAG_MOBIL` | Did client provide mobile phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 1.00 | 1.00 |
| `FLAG_EMP_PHONE` | Did client provide work phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.81 | 1.00 |
| `FLAG_WORK_PHONE` | Did client provide home phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.20 | 0.00 |
| `FLAG_CONT_MOBILE` | Was mobile phone reachable (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 1.00 | 1.00 |
| `FLAG_PHONE` | Did client provide home phone (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.26 | 0.00 |
| `FLAG_EMAIL` | Did client provide email (1=YES, 0=NO) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.16 | 0.00 |
| `CNT_FAM_MEMBERS` | How many family members does client have | DOUBLE | 0.00 | 12 | 1.00 | 21.00 | 2.15 | 2.00 |
| `REGION_RATING_CLIENT` | Our rating of the region where client lives (1,2,3) | BIGINT | 0.00 | 3 | 1.00 | 3.00 | 2.04 | 2.00 |
| `REGION_RATING_CLIENT_W_CITY` | Our rating of the region where client lives with taking city into account (1,2,3) | BIGINT | 0.00 | 4 | -1.00 | 3.00 | 2.01 | 2.00 |
| `HOUR_APPR_PROCESS_START` | Approximately at what hour did the client apply for the loan | BIGINT | 0.00 | 24 | 0.00 | 23.00 | 12.01 | 12.00 |
| `REG_REGION_NOT_LIVE_REGION` | Flag if client's permanent address does not match contact address (1=different, 0=same, at region level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.02 | 0.00 |
| `REG_REGION_NOT_WORK_REGION` | Flag if client's permanent address does not match work address (1=different, 0=same, at region level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.06 | 0.00 |
| `LIVE_REGION_NOT_WORK_REGION` | Flag if client's contact address does not match work address (1=different, 0=same, at region level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.04 | 0.00 |
| `REG_CITY_NOT_LIVE_CITY` | Flag if client's permanent address does not match contact address (1=different, 0=same, at city level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.08 | 0.00 |
| `REG_CITY_NOT_WORK_CITY` | Flag if client's permanent address does not match work address (1=different, 0=same, at city level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.22 | 0.00 |
| `LIVE_CITY_NOT_WORK_CITY` | Flag if client's contact address does not match work address (1=different, 0=same, at city level) | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.17 | 0.00 |
| `EXT_SOURCE_1` | Normalized score from external data source | DOUBLE | 42.12 | 27207 | 0.01 | 0.94 | 0.50 | 0.51 |
| `EXT_SOURCE_2` | Normalized score from external data source | DOUBLE | 0.02 | 38885 | 0.00 | 0.85 | 0.52 | 0.56 |
| `EXT_SOURCE_3` | Normalized score from external data source | DOUBLE | 17.78 | 702 | 0.00 | 0.88 | 0.50 | 0.52 |
| `APARTMENTS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 49.01 | 1543 | 0.00 | 1.00 | 0.12 | 0.09 |
| `BASEMENTAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 56.71 | 2816 | 0.00 | 1.00 | 0.09 | 0.08 |
| `YEARS_BEGINEXPLUATATION_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 46.89 | 175 | 0.00 | 1.00 | 0.98 | 0.98 |
| `YEARS_BUILD_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 65.28 | 130 | 0.00 | 1.00 | 0.75 | 0.75 |
| `COMMONAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.72 | 2042 | 0.00 | 1.00 | 0.05 | 0.02 |
| `ELEVATORS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 51.68 | 181 | 0.00 | 1.00 | 0.09 | 0.00 |
| `ENTRANCES_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.37 | 200 | 0.00 | 1.00 | 0.15 | 0.14 |
| `FLOORSMAX_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 47.84 | 252 | 0.00 | 1.00 | 0.23 | 0.17 |
| `FLOORSMIN_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 66.61 | 198 | 0.00 | 1.00 | 0.24 | 0.21 |
| `LANDAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 57.96 | 2540 | 0.00 | 1.00 | 0.07 | 0.05 |
| `LIVINGAPARTMENTS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 67.25 | 1211 | 0.00 | 1.00 | 0.11 | 0.08 |
| `LIVINGAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.32 | 3848 | 0.00 | 1.00 | 0.11 | 0.08 |
| `NONLIVINGAPARTMENTS_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.41 | 241 | 0.00 | 1.00 | 0.01 | 0.00 |
| `NONLIVINGAREA_AVG` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 53.51 | 2026 | 0.00 | 1.00 | 0.03 | 0.00 |
| `APARTMENTS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 49.01 | 636 | 0.00 | 1.00 | 0.12 | 0.09 |
| `BASEMENTAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 56.71 | 2835 | 0.00 | 1.00 | 0.09 | 0.08 |
| `YEARS_BEGINEXPLUATATION_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 46.89 | 160 | 0.00 | 1.00 | 0.98 | 0.98 |
| `YEARS_BUILD_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 65.28 | 132 | 0.00 | 1.00 | 0.76 | 0.76 |
| `COMMONAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.72 | 2001 | 0.00 | 1.00 | 0.05 | 0.02 |
| `ELEVATORS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 51.68 | 26 | 0.00 | 1.00 | 0.08 | 0.00 |
| `ENTRANCES_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.37 | 30 | 0.00 | 1.00 | 0.15 | 0.14 |
| `FLOORSMAX_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 47.84 | 25 | 0.00 | 1.00 | 0.23 | 0.17 |
| `FLOORSMIN_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 66.61 | 25 | 0.00 | 1.00 | 0.23 | 0.21 |
| `LANDAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 57.96 | 2560 | 0.00 | 1.00 | 0.07 | 0.05 |
| `LIVINGAPARTMENTS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 67.25 | 602 | 0.00 | 1.00 | 0.11 | 0.08 |
| `LIVINGAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.32 | 3842 | 0.00 | 1.00 | 0.11 | 0.08 |
| `NONLIVINGAPARTMENTS_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.41 | 106 | 0.00 | 1.00 | 0.01 | 0.00 |
| `NONLIVINGAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 53.51 | 2025 | 0.00 | 1.00 | 0.03 | 0.00 |
| `APARTMENTS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 49.01 | 918 | 0.00 | 1.00 | 0.12 | 0.09 |
| `BASEMENTAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 56.71 | 2805 | 0.00 | 1.00 | 0.09 | 0.08 |
| `YEARS_BEGINEXPLUATATION_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 46.89 | 169 | 0.00 | 1.00 | 0.98 | 0.98 |
| `YEARS_BUILD_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 65.28 | 129 | 0.00 | 1.00 | 0.75 | 0.76 |
| `COMMONAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.72 | 2034 | 0.00 | 1.00 | 0.05 | 0.02 |
| `ELEVATORS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 51.68 | 43 | 0.00 | 1.00 | 0.08 | 0.00 |
| `ENTRANCES_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.37 | 43 | 0.00 | 1.00 | 0.15 | 0.14 |
| `FLOORSMAX_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 47.84 | 47 | 0.00 | 1.00 | 0.23 | 0.17 |
| `FLOORSMIN_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 66.61 | 44 | 0.00 | 1.00 | 0.24 | 0.21 |
| `LANDAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 57.96 | 2562 | 0.00 | 1.00 | 0.07 | 0.05 |
| `LIVINGAPARTMENTS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 67.25 | 843 | 0.00 | 1.00 | 0.11 | 0.08 |
| `LIVINGAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 48.32 | 3885 | 0.00 | 1.00 | 0.11 | 0.08 |
| `NONLIVINGAPARTMENTS_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 68.41 | 134 | 0.00 | 1.00 | 0.01 | 0.00 |
| `NONLIVINGAREA_MEDI` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 53.51 | 2030 | 0.00 | 1.00 | 0.03 | 0.00 |
| `TOTALAREA_MODE` | Normalized information about building where the client lives, What is average (_AVG suffix), modus (_MODE suffix), median (_MEDI suffix) apartment size, common area, living area, age of building, number of elevators, number of entrances, state of the building, number of floor | DOUBLE | 46.41 | 3820 | 0.00 | 1.00 | 0.11 | 0.07 |
| `OBS_30_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings with observable 30 DPD (days past due) default | DOUBLE | 0.06 | 28 | 0.00 | 354.00 | 1.45 | 0.00 |
| `DEF_30_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings defaulted on 30 DPD (days past due) | DOUBLE | 0.06 | 8 | 0.00 | 34.00 | 0.14 | 0.00 |
| `OBS_60_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings with observable 60 DPD (days past due) default | DOUBLE | 0.06 | 27 | 0.00 | 351.00 | 1.44 | 0.00 |
| `DEF_60_CNT_SOCIAL_CIRCLE` | How many observation of client's social surroundings defaulted on 60 (days past due) DPD | DOUBLE | 0.06 | 7 | 0.00 | 24.00 | 0.10 | 0.00 |
| `DAYS_LAST_PHONE_CHANGE` | How many days before application did client change phone | DOUBLE | 0.00 | 3579 | -4,361.00 | 0.00 | -1,077.77 | -860.52 |
| `FLAG_DOCUMENT_2` | Did client provide document 2 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_3` | Did client provide document 3 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.79 | 1.00 |
| `FLAG_DOCUMENT_4` | Did client provide document 4 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_5` | Did client provide document 5 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.01 | 0.00 |
| `FLAG_DOCUMENT_6` | Did client provide document 6 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.09 | 0.00 |
| `FLAG_DOCUMENT_7` | Did client provide document 7 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_8` | Did client provide document 8 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.09 | 0.00 |
| `FLAG_DOCUMENT_9` | Did client provide document 9 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_10` | Did client provide document 10 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_11` | Did client provide document 11 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_12` | Did client provide document 12 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_13` | Did client provide document 13 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_14` | Did client provide document 14 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_15` | Did client provide document 15 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_16` | Did client provide document 16 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_17` | Did client provide document 17 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_18` | Did client provide document 18 | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_19` | Did client provide document 19 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_20` | Did client provide document 20 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `FLAG_DOCUMENT_21` | Did client provide document 21 | BIGINT | 0.00 | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_HOUR` | Number of enquiries to Credit Bureau about the client one hour before application | DOUBLE | 12.41 | 3 | 0.00 | 2.00 | 0.00 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_DAY` | Number of enquiries to Credit Bureau about the client one day before application (excluding one hour before application) | DOUBLE | 12.41 | 3 | 0.00 | 2.00 | 0.00 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_WEEK` | Number of enquiries to Credit Bureau about the client one week before application (excluding one day before application) | DOUBLE | 12.41 | 3 | 0.00 | 2.00 | 0.00 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_MON` | Number of enquiries to Credit Bureau about the client one month before application (excluding one week before application) | DOUBLE | 12.41 | 7 | 0.00 | 6.00 | 0.01 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_QRT` | Number of enquiries to Credit Bureau about the client 3 month before application (excluding one month before application) | DOUBLE | 12.41 | 8 | 0.00 | 7.00 | 0.55 | 0.00 |
| `AMT_REQ_CREDIT_BUREAU_YEAR` | Number of enquiries to Credit Bureau about the client one day year (excluding last 3 months before application) | DOUBLE | 12.41 | 16 | 0.00 | 17.00 | 1.98 | 2.00 |


## bureau.csv

행 수: 1,716,428 / 컬럼 수: 17

### 범주형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |
|---|---|---|---|---|---|
| `CREDIT_ACTIVE` | Status of the Credit Bureau (CB) reported credits | VARCHAR | 0.00 | 4 | Closed (62.9%); Active (36.7%); Sold (0.4%); Bad debt (0.0%) |
| `CREDIT_CURRENCY` | Recoded currency of the Credit Bureau credit | VARCHAR | 0.00 | 4 | currency 1 (99.9%); currency 2 (0.1%); currency 3 (0.0%); currency 4 (0.0%) |
| `CREDIT_TYPE` | Type of Credit Bureau credit (Car, cash,...) | VARCHAR | 0.00 | 15 | Consumer credit (72.9%); Credit card (23.4%); Car loan (1.6%); Mortgage (1.1%); Microloan (0.7%) |

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_CURR` | ID of loan in our sample - one loan in our sample can have 0,1,2 or more related previous credits in credit bureau | BIGINT | 0.00 | 305811 | 100,001.00 | 456,255.00 | 278,214.93 | 277,829.00 |
| `SK_ID_BUREAU` |  | BIGINT | 0.00 | 1716428 | 5,000,000.00 | 6,843,457.00 | 5,924,434.49 | 5,925,268.00 |
| `DAYS_CREDIT` | How many days before current application did client apply for Credit Bureau credit | BIGINT | 0.00 | 2923 | -2,922.00 | 0.00 | -1,142.11 | -987.00 |
| `CREDIT_DAY_OVERDUE` | Number of days past due on CB credit at the time of application for related loan in our sample | BIGINT | 0.00 | 942 | 0.00 | 2,792.00 | 0.82 | 0.00 |
| `DAYS_CREDIT_ENDDATE` | Remaining duration of CB credit (in days) at the time of application in Home Credit | DOUBLE | 6.15 | 14096 | -42,060.00 | 31,199.00 | 510.52 | -329.65 |
| `DAYS_ENDDATE_FACT` | Days since CB credit ended at the time of application in Home Credit (only for closed credit) | DOUBLE | 36.92 | 2917 | -42,023.00 | 0.00 | -1,017.44 | -896.27 |
| `AMT_CREDIT_MAX_OVERDUE` | Maximal amount overdue on the Credit Bureau credit so far (at application date of loan in our sample) | DOUBLE | 65.51 | 68251 | 0.00 | 115,987,185.00 | 3,825.42 | 0.00 |
| `CNT_CREDIT_PROLONG` | How many times was the Credit Bureau credit prolonged | BIGINT | 0.00 | 10 | 0.00 | 9.00 | 0.01 | 0.00 |
| `AMT_CREDIT_SUM` | Current credit amount for the Credit Bureau credit | DOUBLE | 0.00 | 236708 | 0.00 | 585,000,000.00 | 354,994.59 | 125,279.05 |
| `AMT_CREDIT_SUM_DEBT` | Current debt on Credit Bureau credit | DOUBLE | 15.01 | 226537 | -4,705,600.32 | 170,100,000.00 | 137,085.12 | 0.00 |
| `AMT_CREDIT_SUM_LIMIT` | Current credit limit of credit card reported in Credit Bureau | DOUBLE | 34.48 | 51726 | -586,406.11 | 4,705,600.32 | 6,229.51 | 0.00 |
| `AMT_CREDIT_SUM_OVERDUE` | Current amount overdue on Credit Bureau credit | DOUBLE | 0.00 | 1616 | 0.00 | 3,756,681.00 | 37.91 | 0.00 |
| `DAYS_CREDIT_UPDATE` | How many days before loan application did last information about the Credit Bureau credit come | BIGINT | 0.00 | 2982 | -41,947.00 | 372.00 | -593.75 | -395.00 |
| `AMT_ANNUITY` | Annuity of the Credit Bureau credit | DOUBLE | 71.47 | 40321 | 0.00 | 118,453,423.50 | 15,712.76 | 3.69 |


## bureau_balance.csv

행 수: 27,299,925 / 컬럼 수: 3

### 범주형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |
|---|---|---|---|---|---|
| `STATUS` | Status of Credit Bureau loan during the month (active, closed, DPD0-30,… [C means closed, X means status unknown, 0 means no DPD, 1 means maximal did during month between 1-30, 2 means DPD 31-60,… 5 means DPD 120+ or sold or written off ] ) | VARCHAR | 0.00 | 8 | C (50.0%); 0 (27.5%); X (21.3%); 1 (0.9%); 5 (0.2%) |

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_BUREAU` |  | BIGINT | 0.00 | 817395 | 5,001,709.00 | 6,842,888.00 | 6,036,297.33 | 6,073,324.00 |
| `MONTHS_BALANCE` | Month of balance relative to application date (-1 means the freshest balance date) | BIGINT | 0.00 | 97 | -96.00 | 0.00 | -30.74 | -25.00 |


## previous_application.csv

행 수: 1,670,214 / 컬럼 수: 37

### 범주형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |
|---|---|---|---|---|---|
| `NAME_CONTRACT_TYPE` | Contract product type (Cash loan, consumer loan [POS] ,...) of the previous application | VARCHAR | 0.00 | 4 | Cash loans (44.8%); Consumer loans (43.7%); Revolving loans (11.6%); XNA (0.0%) |
| `WEEKDAY_APPR_PROCESS_START` | On which day of the week did the client apply for previous application | VARCHAR | 0.00 | 7 | TUESDAY (15.3%); WEDNESDAY (15.3%); MONDAY (15.2%); FRIDAY (15.1%); THURSDAY (14.9%) |
| `FLAG_LAST_APPL_PER_CONTRACT` | Flag if it was last application for the previous contract. Sometimes by mistake of client or our clerk there could be more applications for one single contract | VARCHAR | 0.00 | 2 | Y (99.5%); N (0.5%) |
| `NAME_CASH_LOAN_PURPOSE` | Purpose of the cash loan | VARCHAR | 0.00 | 25 | XAP (55.2%); XNA (40.6%); Repairs (1.4%); Other (0.9%); Urgent needs (0.5%) |
| `NAME_CONTRACT_STATUS` | Contract status (approved, cancelled, ...) of previous application | VARCHAR | 0.00 | 4 | Approved (62.1%); Canceled (18.9%); Refused (17.4%); Unused offer (1.6%) |
| `NAME_PAYMENT_TYPE` | Payment method that client chose to pay for the previous application | VARCHAR | 0.00 | 4 | Cash through the bank (61.9%); XNA (37.6%); Non-cash from your account (0.5%); Cashless from the account of the employer (0.1%) |
| `CODE_REJECT_REASON` | Why was the previous application rejected | VARCHAR | 0.00 | 9 | XAP (81.0%); HC (10.5%); LIMIT (3.3%); SCO (2.2%); CLIENT (1.6%) |
| `NAME_TYPE_SUITE` | Who accompanied client when applying for the previous application | VARCHAR | 49.12 | 7 | Unaccompanied (30.5%); Family (12.8%); Spouse, partner (4.0%); Children (1.9%); Other_B (1.1%) |
| `NAME_CLIENT_TYPE` | Was the client old or new client when applying for the previous application | VARCHAR | 0.00 | 4 | Repeater (73.7%); New (18.0%); Refreshed (8.1%); XNA (0.1%) |
| `NAME_GOODS_CATEGORY` | What kind of goods did the client apply for in the previous application | VARCHAR | 0.00 | 28 | XNA (56.9%); Mobile (13.5%); Consumer Electronics (7.3%); Computers (6.3%); Audio/Video (6.0%) |
| `NAME_PORTFOLIO` | Was the previous application for CASH, POS, CAR, … | VARCHAR | 0.00 | 5 | POS (41.4%); Cash (27.6%); XNA (22.3%); Cards (8.7%); Cars (0.0%) |
| `NAME_PRODUCT_TYPE` | Was the previous application x-sell o walk-in | VARCHAR | 0.00 | 3 | XNA (63.7%); x-sell (27.3%); walk-in (9.0%) |
| `CHANNEL_TYPE` | Through which channel we acquired the client on the previous application | VARCHAR | 0.00 | 8 | Credit and cash offices (43.1%); Country-wide (29.6%); Stone (12.7%); Regional / Local (6.5%); Contact center (4.3%) |
| `NAME_SELLER_INDUSTRY` | The industry of the seller | VARCHAR | 0.00 | 11 | XNA (51.2%); Consumer electronics (23.8%); Connectivity (16.5%); Furniture (3.5%); Construction (1.8%) |
| `NAME_YIELD_GROUP` | Grouped interest rate into small medium and high of the previous application | VARCHAR | 0.00 | 5 | XNA (31.0%); middle (23.1%); high (21.2%); low_normal (19.3%); low_action (5.5%) |
| `PRODUCT_COMBINATION` | Detailed product combination of the previous application | VARCHAR | 0.02 | 17 | Cash (17.1%); POS household with interest (15.8%); POS mobile with interest (13.2%); Cash X-Sell: middle (8.6%); Cash X-Sell: low (7.8%) |

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_PREV` | ID of previous credit in Home credit related to loan in our sample. (One loan in our sample can have 0,1,2 or more previous loan applications in Home Credit, previous application could, but not necessarily have to lead to credit) | BIGINT | 0.00 | 1670214 | 1,000,001.00 | 2,845,382.00 | 1,923,089.14 | 1,923,404.00 |
| `SK_ID_CURR` | ID of loan in our sample | BIGINT | 0.00 | 338857 | 100,001.00 | 456,255.00 | 278,357.17 | 278,671.00 |
| `AMT_ANNUITY` | Annuity of previous application | DOUBLE | 22.29 | 357959 | 0.00 | 418,058.15 | 15,955.12 | 11,234.99 |
| `AMT_APPLICATION` | For how much credit did client ask on the previous application | DOUBLE | 0.00 | 93885 | 0.00 | 6,905,160.00 | 175,233.86 | 71,015.40 |
| `AMT_CREDIT` | Final credit amount on the previous application. This differs from AMT_APPLICATION in a way that the AMT_APPLICATION is the amount for which the client initially applied for, but during our approval process he could have received different amount - AMT_CREDIT | DOUBLE | 0.00 | 86803 | 0.00 | 6,905,160.00 | 196,114.02 | 80,337.01 |
| `AMT_DOWN_PAYMENT` | Down payment on the previous application | DOUBLE | 53.64 | 29278 | -0.90 | 3,060,045.00 | 6,697.40 | 1,347.43 |
| `AMT_GOODS_PRICE` | Goods price of good that client asked for (if applicable) on the previous application | DOUBLE | 23.08 | 93885 | 0.00 | 6,905,160.00 | 227,847.28 | 110,926.86 |
| `HOUR_APPR_PROCESS_START` | Approximately at what day hour did the client apply for the previous application | BIGINT | 0.00 | 24 | 0.00 | 23.00 | 12.48 | 12.00 |
| `NFLAG_LAST_APPL_IN_DAY` | Flag if the application was the last application per day of the client. Sometimes clients apply for more applications a day. Rarely it could also be error in our system that one application is in the database twice | BIGINT | 0.00 | 2 | 0.00 | 1.00 | 1.00 | 1.00 |
| `RATE_DOWN_PAYMENT` | Down payment rate normalized on previous credit | DOUBLE | 53.64 | 207033 | -0.00 | 1.00 | 0.08 | 0.05 |
| `RATE_INTEREST_PRIMARY` | Interest rate normalized on previous credit | DOUBLE | 99.64 | 148 | 0.03 | 1.00 | 0.19 | 0.19 |
| `RATE_INTEREST_PRIVILEGED` | Interest rate normalized on previous credit | DOUBLE | 99.64 | 25 | 0.37 | 1.00 | 0.77 | 0.84 |
| `DAYS_DECISION` | Relative to current application when was the decision about previous application made | BIGINT | 0.00 | 2922 | -2,922.00 | -1.00 | -880.68 | -582.00 |
| `SELLERPLACE_AREA` | Selling area of seller place of the previous application | BIGINT | 0.00 | 2097 | -1.00 | 4,000,000.00 | 313.95 | 3.00 |
| `CNT_PAYMENT` | Term of previous credit at application of the previous application | DOUBLE | 22.29 | 49 | 0.00 | 84.00 | 16.05 | 12.00 |
| `DAYS_FIRST_DRAWING` | Relative to application date of current application when was the first disbursement of the previous application | DOUBLE | 40.30 | 2838 | -2,922.00 | 365,243.00 | 342,209.86 | 365,243.00 |
| `DAYS_FIRST_DUE` | Relative to application date of current application when was the first due supposed to be of the previous application | DOUBLE | 40.30 | 2892 | -2,892.00 | 365,243.00 | 13,826.27 | -831.08 |
| `DAYS_LAST_DUE_1ST_VERSION` | Relative to application date of current application when was the first due of the previous application | DOUBLE | 40.30 | 4605 | -2,801.00 | 365,243.00 | 33,767.77 | -360.86 |
| `DAYS_LAST_DUE` | Relative to application date of current application when was the last due date of the previous application | DOUBLE | 40.30 | 2873 | -2,889.00 | 365,243.00 | 76,582.40 | -537.12 |
| `DAYS_TERMINATION` | Relative to application date of current application when was the expected termination of the previous application | DOUBLE | 40.30 | 2830 | -2,874.00 | 365,243.00 | 81,992.34 | -498.70 |
| `NFLAG_INSURED_ON_APPROVAL` | Did the client requested insurance during the previous application | DOUBLE | 40.30 | 2 | 0.00 | 1.00 | 0.33 | 0.00 |


## credit_card_balance.csv

행 수: 3,840,312 / 컬럼 수: 23

### 범주형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |
|---|---|---|---|---|---|
| `NAME_CONTRACT_STATUS` | Contract status (active signed,...) on the previous credit | VARCHAR | 0.00 | 7 | Active (96.3%); Completed (3.4%); Signed (0.3%); Demand (0.0%); Sent proposal (0.0%) |

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_PREV` | ID of previous credit in Home credit related to loan in our sample. (One loan in our sample can have 0,1,2 or more previous loans in Home Credit) | BIGINT | 0.00 | 104307 | 1,000,018.00 | 2,843,496.00 | 1,904,503.59 | 1,897,537.00 |
| `SK_ID_CURR` | ID of loan in our sample | BIGINT | 0.00 | 103558 | 100,006.00 | 456,250.00 | 278,324.21 | 278,507.00 |
| `MONTHS_BALANCE` | Month of balance relative to application date (-1 means the freshest balance date) | BIGINT | 0.00 | 96 | -96.00 | -1.00 | -34.52 | -28.00 |
| `AMT_BALANCE` | Balance during the month of previous credit | DOUBLE | 0.00 | 1347904 | -420,250.18 | 1,505,902.19 | 58,300.16 | 0.00 |
| `AMT_CREDIT_LIMIT_ACTUAL` | Credit card limit during the month of the previous credit | BIGINT | 0.00 | 181 | 0.00 | 1,350,000.00 | 153,807.96 | 119,111.00 |
| `AMT_DRAWINGS_ATM_CURRENT` | Amount drawing at ATM during the month of the previous credit | DOUBLE | 19.52 | 2267 | -6,827.31 | 2,115,000.00 | 5,961.32 | 0.00 |
| `AMT_DRAWINGS_CURRENT` | Amount drawing during the month of the previous credit | DOUBLE | 0.00 | 187005 | -6,211.62 | 2,287,098.31 | 7,433.39 | 0.00 |
| `AMT_DRAWINGS_OTHER_CURRENT` | Amount of other drawings during the month of the previous credit | DOUBLE | 19.52 | 1832 | 0.00 | 1,529,847.00 | 288.17 | 0.00 |
| `AMT_DRAWINGS_POS_CURRENT` | Amount drawing or buying goods during the month of the previous credit | DOUBLE | 19.52 | 168748 | 0.00 | 2,239,274.16 | 2,968.80 | 0.00 |
| `AMT_INST_MIN_REGULARITY` | Minimal installment for this month of the previous credit | DOUBLE | 7.95 | 312266 | 0.00 | 202,882.01 | 3,540.20 | 0.00 |
| `AMT_PAYMENT_CURRENT` | How much did the client pay during the month on the previous credit | DOUBLE | 20.00 | 163209 | 0.00 | 4,289,207.45 | 10,280.54 | 2,769.05 |
| `AMT_PAYMENT_TOTAL_CURRENT` | How much did the client pay during the month in total on the previous credit | DOUBLE | 0.00 | 182957 | 0.00 | 4,278,315.69 | 7,588.86 | 0.00 |
| `AMT_RECEIVABLE_PRINCIPAL` | Amount receivable for principal on the previous credit | DOUBLE | 0.00 | 1195839 | -423,305.82 | 1,472,316.79 | 55,965.88 | 0.00 |
| `AMT_RECIVABLE` | Amount receivable on the previous credit | DOUBLE | 0.00 | 1338878 | -420,250.18 | 1,493,338.19 | 58,088.81 | 0.00 |
| `AMT_TOTAL_RECEIVABLE` | Total amount receivable on the previous credit | DOUBLE | 0.00 | 1339008 | -420,250.18 | 1,493,338.19 | 58,098.29 | 0.00 |
| `CNT_DRAWINGS_ATM_CURRENT` | Number of drawings at ATM during this month on the previous credit | DOUBLE | 19.52 | 44 | 0.00 | 51.00 | 0.31 | 0.00 |
| `CNT_DRAWINGS_CURRENT` | Number of drawings during this month on the previous credit | BIGINT | 0.00 | 129 | 0.00 | 165.00 | 0.70 | 0.00 |
| `CNT_DRAWINGS_OTHER_CURRENT` | Number of other drawings during this month on the previous credit | DOUBLE | 19.52 | 11 | 0.00 | 12.00 | 0.00 | 0.00 |
| `CNT_DRAWINGS_POS_CURRENT` | Number of drawings for goods during this month on the previous credit | DOUBLE | 19.52 | 133 | 0.00 | 165.00 | 0.56 | 0.00 |
| `CNT_INSTALMENT_MATURE_CUM` | Number of paid installments on the previous credit | DOUBLE | 7.95 | 121 | 0.00 | 120.00 | 20.83 | 15.01 |
| `SK_DPD` | DPD (Days past due) during the month on the previous credit | BIGINT | 0.00 | 917 | 0.00 | 3,260.00 | 9.28 | 0.00 |
| `SK_DPD_DEF` | DPD (Days past due) during the month with tolerance (debts with low loan amounts are ignored) of the previous credit | BIGINT | 0.00 | 378 | 0.00 | 3,260.00 | 0.33 | 0.00 |


## POS_CASH_balance.csv

행 수: 10,001,358 / 컬럼 수: 8

### 범주형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | 상위 5개 값 (비율) |
|---|---|---|---|---|---|
| `NAME_CONTRACT_STATUS` | Contract status during the month | VARCHAR | 0.00 | 9 | Active (91.5%); Completed (7.4%); Signed (0.9%); Demand (0.1%); Returned to the store (0.1%) |

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_PREV` | ID of previous credit in Home Credit related to loan in our sample. (One loan in our sample can have 0,1,2 or more previous loans in Home Credit) | BIGINT | 0.00 | 936325 | 1,000,001.00 | 2,843,499.00 | 1,903,216.60 | 1,896,137.00 |
| `SK_ID_CURR` | ID of loan in our sample | BIGINT | 0.00 | 337252 | 100,001.00 | 456,255.00 | 278,403.86 | 278,708.00 |
| `MONTHS_BALANCE` | Month of balance relative to application date (-1 means the information to the freshest monthly snapshot, 0 means the information at application - often it will be the same as -1 as many banks are not updating the information to Credit Bureau regularly ) | BIGINT | 0.00 | 96 | -96.00 | -1.00 | -35.01 | -28.00 |
| `CNT_INSTALMENT` | Term of previous credit (can change over time) | DOUBLE | 0.26 | 73 | 1.00 | 92.00 | 17.09 | 12.00 |
| `CNT_INSTALMENT_FUTURE` | Installments left to pay on the previous credit | DOUBLE | 0.26 | 79 | 0.00 | 85.00 | 10.48 | 7.00 |
| `SK_DPD` | DPD (days past due) during the month of previous credit | BIGINT | 0.00 | 3400 | 0.00 | 4,231.00 | 11.61 | 0.00 |
| `SK_DPD_DEF` | DPD during the month with tolerance (debts with low loan amounts are ignored) of the previous credit | BIGINT | 0.00 | 2307 | 0.00 | 3,595.00 | 0.65 | 0.00 |


## installments_payments.csv

행 수: 13,605,401 / 컬럼 수: 8

### 수치형 컬럼

| 컬럼명 | 설명 | dtype | 결측률(%) | 카디널리티 | min | max | mean | median |
|---|---|---|---|---|---|---|---|---|
| `SK_ID_PREV` | ID of previous credit in Home credit related to loan in our sample. (One loan in our sample can have 0,1,2 or more previous loans in Home Credit) | BIGINT | 0.00 | 997752 | 1,000,001.00 | 2,843,499.00 | 1,903,364.97 | 1,895,676.00 |
| `SK_ID_CURR` | ID of loan in our sample | BIGINT | 0.00 | 339587 | 100,001.00 | 456,255.00 | 278,444.88 | 278,656.00 |
| `NUM_INSTALMENT_VERSION` | Version of installment calendar (0 is for credit card) of previous credit. Change of installment version from month to month signifies that some parameter of payment calendar has changed | DOUBLE | 0.00 | 65 | 0.00 | 178.00 | 0.86 | 1.00 |
| `NUM_INSTALMENT_NUMBER` | On which installment we observe payment | BIGINT | 0.00 | 277 | 1.00 | 277.00 | 18.87 | 8.00 |
| `DAYS_INSTALMENT` | When the installment of previous credit was supposed to be paid (relative to application date of current loan) | DOUBLE | 0.00 | 2922 | -2,922.00 | -1.00 | -1,042.27 | -818.56 |
| `DAYS_ENTRY_PAYMENT` | When was the installments of previous credit paid actually (relative to application date of current loan) | DOUBLE | 0.02 | 3039 | -4,921.00 | -1.00 | -1,051.11 | -827.45 |
| `AMT_INSTALMENT` | What was the prescribed installment amount of previous credit on this installment | DOUBLE | 0.00 | 902539 | 0.00 | 3,771,487.85 | 17,050.91 | 8,829.91 |
| `AMT_PAYMENT` | What the client actually paid on previous credit on this installment | DOUBLE | 0.02 | 944235 | 0.00 | 3,771,487.85 | 17,238.22 | 8,149.81 |

