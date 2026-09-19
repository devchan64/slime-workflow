#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/script_logging.sh"
cd "$SCRIPT_LOG_ROOT"
printf '%s/workflow/validate 계약 및 결정적 변환 테스트 시작\n' "$(date -Iseconds)"
python -m compileall -q workflow
python -m unittest \
  workflow.nodes.concept_image.tests.test_nodes \
  workflow.nodes.character_sprite.tests.test_nodes \
  workflow.nodes.midi_trim_bars.tests.test_node \
  workflow.nodes.audio_encode_mp3_v2.tests.test_node \
  workflow.nodes.audio_render_wav_v2.tests.test_node \
  workflow.nodes.audio_render_planner_v2.tests.test_node
