# archive/amex — 이전 프로젝트 버전 (참고용, 현재 로드맵과 무관)

이 폴더는 현재 진행 중인 **Home Credit Default Risk** 프로젝트로 전환하기 전, American Express Default Prediction(Kaggle, CC0) 데이터로 진행했던 이전 버전의 작업 내역입니다.

**왜 전환했는가**: AMEX 데이터는 단일 파일에 익명화된 190개 집계 feature만 제공해 "왜 이 feature가 중요한가"를 설명하기 어려웠습니다. 해석 가능한 feature 구조가 필요해, 8개 원본 테이블이 의미가 분명한 컬럼으로 구성된 Home Credit 데이터로 전환했습니다. 자세한 경위는 저장소 루트의 [README.md](../../README.md)와 [PROJECT_GUIDELINES.md](../../PROJECT_GUIDELINES.md) 참고.

이 폴더 안의 문서/스크립트는 Phase 1(데이터 검증)~Phase 3(feature engineering, baseline vs main 비교) 단계까지 진행했던 결과물이며, **현재 프로젝트의 모델·API·배포와는 무관합니다.**
