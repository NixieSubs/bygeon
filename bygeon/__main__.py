import os
import sys

if not __package__:
    source_path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, source_path)

from bygeon.main import main

if __name__ == "__main__":
    main()
