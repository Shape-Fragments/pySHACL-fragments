import unittest
from rdflib import Graph
from rdflib.compare import isomorphic

from examples import example3, example4, example5, example6, example7, example8, example_qvc, example_class, \
    example_targetClass
from pyshacl import validate


def get_correct_subgraph(input_file):
    output_file = input_file.return_output_file()
    correct_output = Graph().parse(format="turtle", data=output_file)
    return correct_output


def get_predicted_subgraph(input_file):
    shapes_file = input_file.return_shapes_file()
    data_file = input_file.return_data_file()
    _, _, _, subgraph = validate(data_file, shacl_graph=shapes_file,
                                 data_graph_format="turtle",
                                 shacl_graph_format="turtle",
                                 inference='rdfs', debug=True,
                                 serialize_report_graph=True,
                                 return_paths=True)
    predicted_output = Graph()
    for triple in subgraph:
        print(triple)
        predicted_output.add(triple)
    return predicted_output


class TestValidateSubgraph(unittest.TestCase):

    def test_example3(self):
        correct_subgraph = get_correct_subgraph(example3)
        subgraph = get_predicted_subgraph(example3)
        self.assertTrue(isomorphic(correct_subgraph, subgraph))

    def test_example4(self):
        self.assertTrue(isomorphic(get_correct_subgraph(example4), get_predicted_subgraph(example4)))

    def test_example5(self):
        self.assertTrue(isomorphic(get_correct_subgraph(example5), get_predicted_subgraph(example5)))

    def test_example6(self):
        self.assertTrue(isomorphic(get_correct_subgraph(example6), get_predicted_subgraph(example6)))

    def test_example7(self):
        self.assertTrue(isomorphic(get_correct_subgraph(example7), get_predicted_subgraph(example7)))

    def test_example8(self):
        self.assertTrue(isomorphic(get_correct_subgraph(example8), get_predicted_subgraph(example8)))

    def test_example_qvc(self):
        self.assertTrue(isomorphic(get_correct_subgraph(example_qvc), get_predicted_subgraph(example_qvc)))

    def test_example_class(self):
        self.assertTrue(isomorphic(get_correct_subgraph(example_class), get_predicted_subgraph(example_class)))

    def test_example_targetClass(self):
        self.assertTrue(
            isomorphic(get_correct_subgraph(example_targetClass), get_predicted_subgraph(example_targetClass)))


if __name__ == '__main__':
    unittest.main()
