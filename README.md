# New Release Crawler (v0.7)

주요 금융 규제 및 표준 제정 기관의 최신 보도자료를 모니터링하고, 설정된 키워드(ESG, AI 등)에 해당하는 소식을 이메일로 자동 발송하는 크롤러입니다.

## 🚀 주요 기능
- **자동 모니터링**: GitHub Actions를 통해 매일 정해진 시간(KST 오전 9시)에 크롤링을 수행합니다.
- **다양한 소스**: FSB, BCBS, NGFS, PCAF(Global/Korea), 금융위원회(FSC), 금융감독원(FSS)을 지원합니다.
- **스마트 필터링**: 
  - 금융위/금감원 자료는 핵심 키워드(ESG, 기후, 탄소, AI, 인공지능 등)를 기준으로 필터링하여 관련 소식만 메인으로 발송합니다.
  - 그 외 일반 보도자료는 '참고' 섹션에 포함됩니다.
- **중복 방지**: `history.json` 파일을 통해 이미 발송한 항목은 중복 알림을 보내지 않습니다.
- **이메일 알림**: Gmail SMTP를 사용하여 깔끔한 HTML 형식의 리포트를 발송합니다.

## 🛠 모니터링 대상 기관
- **FSB** (Financial Stability Board)
- **BCBS** (Basel Committee on Banking Supervision)
- **NGFS** (Network for Greening the Financial System)
- **PCAF** (Partnership for Carbon Accounting Financials)
- **금융위원회** (FSC)
- **금융감독원** (FSS)

## ⚙️ 설정 방법 (GitHub Actions)

이 프로젝트를 자신의 GitHub 저장소에 올린 후, 아래 설정을 완료해야 정상적으로 작동합니다.

### 1. Gmail 앱 비밀번호 발급
- Google 계정의 **2단계 인증**을 활성화합니다.
- [앱 비밀번호 페이지](https://myaccount.google.com/apppasswords)에서 'New Release Crawler'용 16자리 앱 비밀번호를 생성하고 복사합니다.

### 2. GitHub Secrets 등록
GitHub 저장소의 **Settings > Secrets and variables > Actions** 메뉴에서 다음 3가지 항목을 추가합니다.

| 이름 | 설명 | 예시 |
| :--- | :--- | :--- |
| `GMAIL_USER` | 발송에 사용할 Gmail 주소 | `your-email@gmail.com` |
| `GMAIL_APP_PASSWORD` | 위에서 발급받은 16자리 앱 비밀번호 | `abcd efgh ijkl mnop` |
| `RELEASE_CRAWLER_RECIPIENTS` | 수신할 이메일 주소들 (쉼표로 구분) | `user1@kpmg.com, user2@gmail.com` |

### 3. Workflow 권한 설정
`history.json` 업데이트를 위해 권한 설정이 필요합니다.
- **Settings > Actions > General**로 이동합니다.
- **Workflow permissions** 섹션에서 **Read and write permissions**를 선택하고 저장합니다.

## 📂 폴더 구조
```text
├── .github/workflows/
│   └── daily_crawler.yml   # GitHub Actions 실행 설정
├── new_release_crawler.py      # 크롤링 및 이메일 발송 로직
├── requirements.txt            # 라이브러리 의존성
├── history.json                # 크롤링 이력 데이터
└── README.md                   # 프로젝트 설명서
```

## 📝 라이선스
본 프로젝트는 내부 업무 자동화 용도로 제작되었습니다.
