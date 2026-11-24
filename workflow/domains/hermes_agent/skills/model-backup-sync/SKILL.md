---
name: model-backup-sync
description: 로컬 모델과 Samba 백업을 비교하고 동기화 상태를 확인한다.
---
# 모델 백업 동기화

1. 격리 대화에서는 `/runtime/.venv/bin/python /control/management-status.py model-backup-models`, `model-backup-history`, `model-backup-compare 모델이름`으로 목록·이력·비교 요약을 조회한다. 모델 관리 화면은 `model-downloads` 서비스의 `backup-models`, `backup-metadata`, `backup-compare`로 상세 정보를 조회한다. 조회할 수 없으면 결과를 추측하지 않는다.
2. `backup-compare`의 크기·수정 시각 비교는 내용 검증이 아니다. `backup-verify` 작업은 SHA-256으로 비교하며 `backup-verify-status`와 `backup-verify-history`에서 결과를 확인한다. 작업이 완료돼도 누락·불일치·확인 불가 파일이 없는지 따로 확인한다.
3. `backup-sync`는 최신 스냅샷과 SHA-256 및 모델 메타정보가 같으면 재사용하고, 다르면 선택 모델 전체를 새 스냅샷으로 저장해 복사본을 검증한다. 새 스냅샷은 모델 크기만큼 공간이 더 필요하다. 사용자가 요청한 모델을 확인하고 진행 상태와 실제 결과를 확인한다. 원본 또는 기존 백업 파일을 삭제하지 않는다.
4. 매니페스트에서 선언된 해시와 실제 파일 관측 해시를 구분한다. 파일 삭제를 위한 판단에는 완전한 백업 검증과 복원 가능성 확인이 필요하다. 경로·마운트·작업 상태를 확인할 수 없다면 그 사실을 알린다.
