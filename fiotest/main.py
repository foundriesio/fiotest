import logging
import sys

import yaml

from fiotest.runner import SpecRunner
from fiotest.spec import TestSpec

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger()


def main(spec: TestSpec):
    runner = SpecRunner(spec)
    runner.start()
    runner.join()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: %s <test-spec.yml>" % sys.argv[0])
    with open(sys.argv[1]) as f:
        data = yaml.safe_load(f)
    main(TestSpec.parse_obj(data))
