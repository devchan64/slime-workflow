"""Isolated Python 3.10 worker for the AnimationGPT pose pipeline."""
import json
import sys
from pathlib import Path


def main():
    import numpy as np
    from workflow.domains.animationgpt.inference import generate_motion

    request = json.loads(sys.stdin.read())
    output = Path(request['output']).resolve()
    joints, metadata = generate_motion(request['prompt'], request['seed'], request['source_root'], request['model_root'])
    np.save(output / 'joints.npy', joints, allow_pickle=False)
    (output / 'motion.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
