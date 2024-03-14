from argparse import ArgumentParser
import sys
import pathlib
from src.display.diagram_mpl import Diagram
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox

def main(parser: ArgumentParser) -> int:
    args = parser.parse_args()
    SOURCEPATH = pathlib.Path(args.sourcepath)
    OUTPATH = pathlib.Path(args.outpath)
    d = Diagram(interactive=True, show_title=True, diagram="3.5.5.4.3.3")
    d.show_diagram()
    plt.show()
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description="SOME DESCRIPTION OF THAT SCRIPT")
    parser.add_argument('-s', '--sourcepath', type=str,
            default="some/default/value",
            help="Source files for this script.")
    parser.add_argument('-o', '--outpath', type=str,
            default="some/default/value",
            help="Path to store results of this script.")
    parser.add_argument('-v', '--verbose', action='store_true',
            help="Enable verbose output.")
    sys.exit(main(parser))


