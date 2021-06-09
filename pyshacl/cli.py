#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

from os import path
from rdflib import Graph
from rdflib.compare import isomorphic

sys.path.append("..")  # This line was added, otherwise ModuleNotFoundError: No module named 'pyshacl'
from pyshacl import __version__, validate
from pyshacl.errors import ReportableRuntimeError, ValidationFailure


class ShowVersion(argparse.Action):
    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        super(ShowVersion, self).__init__(
            option_strings=option_strings, dest=dest, default=default, nargs=0, help=help
        )

    def __call__(self, parser, namespace, values, option_string=None):
        sys.stderr.write("PySHACL Version: " + str(__version__) + "\n")
        parser.exit()


parser = argparse.ArgumentParser(description='PySHACL {} command line tool.'.format(str(__version__)))
parser.add_argument(
    'data', metavar='DataGraph', type=argparse.FileType('rb'), help='The file containing the Target Data Graph.'
)
parser.add_argument(
    '-s', '--shacl', dest='shacl', action='store', nargs='?', help='A file containing the SHACL Shapes Graph.'
)
parser.add_argument(
    '-e',
    '--ont-graph',
    dest='ont',
    action='store',
    nargs='?',
    help='A file path or URL to a docucument containing extra ontological information to mix into ' 'the data graph.',
)
parser.add_argument(
    '-i',
    '--inference',
    dest='inference',
    action='store',
    default='none',
    choices=('none', 'rdfs', 'owlrl', 'both'),
    help='Choose a type of inferencing to run against the Data Graph before validating.',
)
parser.add_argument(
    '-m',
    '--metashacl',
    dest='metashacl',
    action='store_true',
    default=False,
    help='Validate the SHACL Shapes graph against the shacl-shacl '
         'Shapes Graph before before validating the Data Graph.',
)
parser.add_argument(
    '--imports',
    dest='imports',
    action='store_true',
    default=False,
    help='Allow import of sub-graphs defined in statements with owl:imports.',
)
parser.add_argument(
    '-a',
    '--advanced',
    dest='advanced',
    action='store_true',
    default=False,
    help='Enable features from the SHACL Advanced Features specification.',
)
parser.add_argument(
    '-j',
    '--js',
    dest='js',
    action='store_true',
    default=False,
    help='Enable features from the SHACL-JS Specification.',
)
parser.add_argument('--abort', dest='abort', action='store_true', default=False, help='Abort on first error.')
parser.add_argument(
    '-d', '--debug', dest='debug', action='store_true', default=False, help='Output additional runtime messages.'
)
parser.add_argument(
    '-f',
    '--format',
    dest='format',
    action='store',
    help='Choose an output format. Default is \"human\".',
    default='human',
    choices=('human', 'turtle', 'xml', 'json-ld', 'nt', 'n3'),
)
parser.add_argument(
    '-df',
    '--data-file-format',
    dest='data_file_format',
    action='store',
    help='Explicitly state the RDF File format of the input DataGraph file. Default=\"auto\".',
    default='auto',
    choices=('auto', 'turtle', 'xml', 'json-ld', 'nt', 'n3'),
)
parser.add_argument(
    '-sf',
    '--shacl-file-format',
    dest='shacl_file_format',
    action='store',
    help='Explicitly state the RDF File format of the input SHACL file. Default=\"auto\".',
    default='auto',
    choices=('auto', 'turtle', 'xml', 'json-ld', 'nt', 'n3'),
)
parser.add_argument(
    '-ef',
    '--ont-file-format',
    dest='ont_file_format',
    action='store',
    help='Explicitly state the RDF File format of the extra ontology file. Default=\"auto\".',
    default='auto',
    choices=('auto', 'turtle', 'xml', 'json-ld', 'nt', 'n3'),
)
parser.add_argument('-V', '--version', action=ShowVersion, help='Show PySHACL version and exit.')
parser.add_argument(
    '-o',
    '--output',
    dest='output',
    nargs='?',
    type=argparse.FileType('w'),
    help='Send output to a file (defaults to stdout).',
    default=sys.stdout,
)
parser.add_argument(
    '-rs',
    '--return_subgraphs',
    dest='return_subgraphs',
    default=False,
    help='Enable data graph validation.',
)
parser.add_argument(
    '-eo',
    '--expected_output',
    dest='expected_output',
    # type=argparse.FileType('rb'),
    action='store',
    nargs='?',
    help='The file containing the expected output.',
)


# parser.add_argument('-h', '--help', action="help", help='Show this help text.')


def main():
    basename = os.path.basename(sys.argv[0])
    if basename == "__main__.py":
        parser.prog = "python3 -m pyshacl"
    args = parser.parse_args()
    validator_kwargs = {'debug': args.debug}
    if args.shacl is not None:
        validator_kwargs['shacl_graph'] = args.shacl
    if args.ont is not None:
        validator_kwargs['ont_graph'] = args.ont
    if args.format != 'human':
        validator_kwargs['serialize_report_graph'] = args.format
    if args.inference != 'none':
        validator_kwargs['inference'] = args.inference
    if args.imports:
        validator_kwargs['do_owl_imports'] = True
    if args.metashacl:
        validator_kwargs['meta_shacl'] = True
    if args.advanced:
        validator_kwargs['advanced'] = True
    if args.js:
        validator_kwargs['js'] = True
    if args.abort:
        validator_kwargs['abort_on_error'] = True
    if args.shacl_file_format:
        f = args.shacl_file_format
        if f != "auto":
            validator_kwargs['shacl_graph_format'] = f
    if args.ont_file_format:
        f = args.ont_file_format
        if f != "auto":
            validator_kwargs['ont_graph_format'] = f
    if args.data_file_format:
        f = args.data_file_format
        if f != "auto":
            validator_kwargs['data_graph_format'] = f
    try:
        is_conform, v_graph, v_text, triples = validate(args.data, **validator_kwargs)
        subgraph = Graph()  # This is the conforming subgraph (containing paths of conforming focus nodes)
        for triple in triples:
            subgraph.add(triple)
        if isinstance(v_graph, BaseException):
            raise v_graph
    except ValidationFailure as vf:
        args.output.write("Validator generated a Validation Failure result:\n")
        args.output.write(str(vf.message))
        args.output.write("\n")
        sys.exit(1)
    except ReportableRuntimeError as rre:
        sys.stderr.write("Validator encountered a Runtime Error:\n")
        sys.stderr.write(str(rre.message))
        sys.stderr.write("\nIf you believe this is a bug in pyshacl, open an Issue on the pyshacl github page.\n")
        sys.exit(2)
    except NotImplementedError as nie:
        sys.stderr.write("Validator feature is not implemented:\n")
        sys.stderr.write(str(nie.args[0]))
        sys.stderr.write("\nIf your use-case requires this feature, open an Issue on the pyshacl github page.\n")
        sys.exit(3)
    except RuntimeError as re:
        import traceback

        traceback.print_tb(re.__traceback__)
        sys.stderr.write("\n\nValidator encountered a Runtime Error. Please report this to the PySHACL issue tracker.")
        sys.exit(2)

    if args.expected_output is not None:
        with open(args.expected_output) as f:
            expected_output = f.read()
        expected_output = Graph().parse(format="turtle", data=expected_output)
        # Compare the (conforming) subgraph output produced by code (validate function) with the expected output
        is_isomorphic = isomorphic(expected_output, subgraph)
        sys.stdout.write(f"IS ISOMORPHIC: {str(is_isomorphic)}\n")
        if not is_isomorphic:
            missing = expected_output - subgraph
            print("MISSING TRIPLES:")
            for triple_binary_string in sorted(missing.serialize(format='nt').splitlines()):
                if triple_binary_string:
                    print(triple_binary_string.decode('ascii'))
            excess = subgraph - expected_output
            print("EXCESS TRIPLES:")
            for triple_binary_string in sorted(excess.serialize(format='nt').splitlines()):
                if triple_binary_string:
                    print(triple_binary_string.decode('ascii'))

    if args.return_subgraphs:
        if args.format == 'human':
            subgraph = subgraph.serialize(format='nt')
        else:
            subgraph = subgraph.serialize(format=args.format)
        if isinstance(subgraph, bytes):
            subgraph = subgraph.decode('utf-8')
        args.output.write(subgraph)

    elif args.format == 'human':
        args.output.write(v_text)
    else:
        if isinstance(v_graph, bytes):
            v_graph = v_graph.decode('utf-8')
        args.output.write(v_graph)
    args.output.close()
    if is_conform:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
