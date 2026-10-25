# 배경음악 생성 워크플로우

현행 음악 생성기는 **HeartMuLa 3B → Demucs htdemucs**다. 가사가 있는 원곡을 생성하고 MR을 분리해 두 버전을 비교한다. 최종 WAV와 320kbps MP3를 보관한다. MIDI는 출력하지 않는다. MiniMax·Magenta·ACE-Step은 현행 생성 경로가 아니다. [과거 전환·실험 기록](HISTORY.md)은 재현 참고용이다.

## 1. 준비

관리도구의 **소리 관리 → HeartMuLa 3B**를 연다. 모델 준비 상태와 GPU 검증 상태를 확인한다. GUI는 클라이언트이며 모든 작업은 공용 명령 게이트웨이·작업 서비스·GPU 대기열로 실행한다. [관리도구 클라이언트 가이드](../../workflows/management-clients.md)를 함께 따른다.

| 역할 | 고정 구성 |
|---|---|
| 음악 생성 | HeartMuLa/HeartMuLa-oss-3B-happy-new-year, NF4/BF16 |
| 오디오 복원 | HeartCodec-oss-20260123, FP32, 디코더 창 7.44초 |
| MR 분리 | Demucs 4.0.1, htdemucs, CUDA, 7초 구간 |
| MP3 인코딩 | lameenc 1.9.0, 320kbps |

모델·라이브러리 리비전은 [runtime.py](heartmula/runtime.py), 분리 체크포인트와 SHA-256은 [separation.py](heartmula/separation.py)에 고정한다. 전용 환경은 `.venv-music-heartmula`, 의존성은 [requirements.txt](heartmula/requirements.txt)다. 모델 연산은 CUDA에서 순차 실행하며 CPU 추론으로 대체하지 않는다. MP3 인코딩·파일 입출력은 모델 추론이 아니다.

캐시는 `.model/music/music-heartmula/`만 사용한다. 모델 준비는 로컬 파일·인덱스와 해시를 검사한다. 모델 파일 준비와 실제 GPU 생성 검증은 다르며 누락·실패 시 원인을 고쳐야 한다. Demucs는 준비 단계에서 공식 체크포인트 다운로드와 해시 검증을 수행한다.

## 2. 예제 선택과 입력

**예제 프롬프트 목록 → 이전/다음 예제 페이지 → 예제 선택 → 선택한 예제를 폼에 불러오기**를 누른다. 31개 맵 예제와 안개 호수 허스키 보컬 비교 예제, 총 32개를 페이지당 10개씩 표시한다. 페이지 이동은 해당 페이지 첫 예제를 미리 보며, 예제 선택만으로 입력을 바꾸지 않는다. 불러오기는 현재 입력을 덮어쓰지만 작업을 접수하지 않는다. 제작 기준 예제는 [heartmula/examples.yaml](heartmula/examples.yaml)에서 Git으로 관리한다. 이전 8행 실험 파일 [iseulon_vocal_mr.yaml](heartmula/iseulon_vocal_mr.yaml)은 과거 재현 입력이다.

| 입력 | 의미 |
|---|---|
| 음악 태그 | 쉼표로 구분한 장르·악기·분위기·보컬 표현. `prompt` 계약으로 저장 |
| 가사·구간 태그 | `[Intro]`, `[Verse]`, `[Chorus]`, `[Outro]`와 실제 가사. 무보컬은 생성 후 MR 분리로 확보 |
| 최대 출력 시간 | 기본값 300초(5분), 허용 범위 5~300초 상한. 목표·최소 길이가 아니며 밀리초로 환산 |
| 시드 | 비교 실험의 난수 입력. 랜덤 버튼은 값만 변경 |
| 이력 태그 | 결과 구분용 이름. 모델 입력에 포함하지 않음 |

현재 31개 예제는 맵별 장르·악기 편성을 개별 지정하고 도입 2행·변화 2행·후렴 4행·마무리 2행의 가사로 구성한다. 60~90초 안팎은 실험 목표이며 최대 출력 기본값 300초와 구분한다. 태그·가사의 반영과 MR의 선율 유지·종결은 생성 후 청취 검수가 필요하다. 기존 대기 작업과 등록 에셋에는 변경을 소급하지 않는다.

과거 약 1분 곡은 짧은 가사로 실험했다. 이슬온 예제의 6행 가사·상한 120초에서 70.32초가 나온 것은 한 번의 관측이며 행 수와 길이의 고정 공식이 아니다. 상한을 60초로 지정하면 곡 중간에 잘릴 수 있다. 종료 토큰(EOS)으로 먼저 끝날 수 있고 EOS도 음악적 종지를 보증하지 않는다. 보컬 억제·종료 토큰 억제·페이드·자동 음량 조절·반복 접합은 적용하지 않는다.

## 3. 대기열 등록과 진행 확인

입력과 최종 원문·단어 수를 확인하고 **대기열에 추가 → 확인 후 대기열에 추가**로 접수한다. 취소하면 실행하지 않는다. 실행 중인 다른 작업을 중단하지 않으며 같은 GPU 대기열에서 순서를 기다린다.

준비 → 생성 → 디코딩 → MR 분리 → MP3 저장 순으로 진행한다. 공용 상태에는 단계·예상 남은 시간·완료 시각·추정 근거·VRAM 관측 피크가 기록된다. 충분한 표본이 없으면 계산 중으로 표시한다. 관측 피크는 샘플 간 순간 피크를 놓칠 수 있다.

CLI도 동일한 서비스와 기록을 사용한다.

```bash
.venv-management/bin/python tools/manager.py command music-heartmula generate --prompt 'piano,harp,flute,acoustic,peaceful,female vocals' --lyrics $'[Verse]\nMorning warms the village lane\nDewdrops shine after the rain\n[Chorus]\nGentle roads will lead us home\n[Outro]' --duration-seconds 300 --seed 7 --tag bgm-test --detach
.venv-management/bin/python tools/manager.py command music-heartmula status <생성ID>
.venv-management/bin/python tools/manager.py command music-heartmula logs <생성ID>
```

## 4. 결과 비교와 다운로드

완료된 이력 선택 → **결과 조회**에서 실제 길이와 세 재생기를 확인한다.

| 결과 | WAV | MP3 | 사용 |
|---|---|---|---|
| 가사 있는 버전 · 원곡 | music.wav | music.mp3 | 보컬 BGM 후보·비교 기준 |
| 가사 없는 버전 · MR | mr.wav | mr.mp3 | 무보컬 BGM 후보 |
| 분리 보컬 | vocals.wav | vocals.mp3 | 보컬 분리 품질 확인 |

원곡은 48kHz, MR·분리 보컬은 44.1kHz stereo다. 분리 WAV는 FLOAT다. MP3는 320kbps이며 PCM16 변환 범위를 넘는 샘플은 클리핑한다. WAV 원본에는 이 처리를 적용하지 않는다. 기존 MP3 미생성 이력을 조회해도 자동 변환하지 않는다.

검수 항목은 곡 분위기·악기 구성·보컬 잔향·악기 손실·무음·끝맺음이다. 원곡과 MR을 같은 구간에서 번갈아 듣는다. 화면의 재생 성공과 음질 승인은 구분한다. 심리스 루프와 MR 완전 무보컬은 보장하지 않는다.

## 5. 채택과 에셋 전달

사용자가 채택한 결과만 `slime-assets`에 등록한다. 관리 ID·불변 버전·출처 생성 ID·실행 시도·SHA-256을 보존하며, 맵별 지정 파일에 사용할 버전을 명시한다. 생성기에서 게임에 자동 게시하지 않는다. 보컬 버전도 사용할 경우 MR과 별개 에셋으로 등록한다. 프론트 재생·음량 설정·맵 전환 설계는 생성기 책임과 구분한다.

## 6. 이력과 실패 처리

작업은 `.tmp/test/music-heartmula/<생성ID>/`, 실행별 산출물은 `attempts/<UUID>/`, 색인은 `.tmp/manager-current/music-heartmula/`에 보존한다. 요청·최종 입력·모델 준비 기록·결과·종료 이유·로그·측정치를 GUI/CLI에서 공유한다.

실패 시 로그에서 최초 실패 단계를 확인한다. 분리·MP3 저장 실패는 전체 작업 실패이며 앞서 저장한 WAV는 남을 수 있다. **생성 재개**는 같은 생성 ID 아래 새 시도를 시작하며 음악 토큰이나 분리 단계부터 이어지는 기능이 아니다. 선택 삭제·이력 초기화는 입력 사본·모든 시도·결과·로그를 실제 삭제하므로 승인 에셋은 먼저 별도 등록한다. 대기·실행 중 작업은 삭제할 수 없다.

## 공식 자료

- [HeartMuLa 모델 카드](https://huggingface.co/HeartMuLa/HeartMuLa-oss-3B-happy-new-year), [HeartCodec](https://huggingface.co/HeartMuLa/HeartCodec-oss-20260123), [HeartLib](https://github.com/HeartMuLa/heartlib): Apache-2.0 안내.
- [Demucs](https://github.com/facebookresearch/demucs): MIT 안내.
- 코드·가중치 재배포 조건과 생성 음악의 권리 검토는 구분한다. 사용 권한이 있는 가사를 입력하며 라이선스 표기만으로 결과의 비침해가 보장되지는 않는다.
