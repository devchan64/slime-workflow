"""musicgen_small 노드 entrypoint."""

from workflow.nodes.musicgen_small.application import MusicgenSmallGenerationModule


def ordered_stages():
    return [MusicgenSmallGenerationModule()]
