import unittest
from rdflib import Graph
from rdflib.compare import isomorphic

from examples import example3, example4, example5, example6, example7, example8
from pyshacl import validate


def get_correct_subgraph(input_file):
    output_file = input_file.return_output_file()
    correct_output = Graph().parse(format="turtle", data=output_file)
    return correct_output


def get_predicted_subgraph(input_file):
    shapes_file = input_file.return_shapes_file()
    data_file = input_file.return_data_file()
    _, _, _, dict_paths = validate(data_file, shacl_graph=shapes_file,
                                   data_graph_format="turtle",
                                   shacl_graph_format="turtle",
                                   inference='rdfs', debug=True,
                                   serialize_report_graph=True)
    predicted_output = Graph()
    for focus in dict_paths:
        for triple in dict_paths[focus]:
            predicted_output.add(triple)
    return predicted_output


class TestValidateSubgraph(unittest.TestCase):

    def test_validate_subgraph(self):
        """
        Compare the (conforming) subgraph output produced by code (validate function) with the expected output
        """
        self.assertEqual(isomorphic(get_correct_subgraph(example3), get_predicted_subgraph(example3)), True)
        self.assertEqual(isomorphic(get_correct_subgraph(example4), get_predicted_subgraph(example4)), True)
        self.assertEqual(isomorphic(get_correct_subgraph(example5), get_predicted_subgraph(example5)), True)
        self.assertEqual(isomorphic(get_correct_subgraph(example6), get_predicted_subgraph(example6)), True)
        self.assertEqual(isomorphic(get_correct_subgraph(example7), get_predicted_subgraph(example7)), True)
        self.assertEqual(isomorphic(get_correct_subgraph(example8), get_predicted_subgraph(example8)), True)


if __name__ == '__main__':
    unittest.main()
