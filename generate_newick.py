import os
import argparse

from grapetree import module

parser = argparse.ArgumentParser(description='Generate a Newick file from a file containing allele profiles.')
parser.add_argument('profile_file', help='Full path and filename for the profile file')
args = parser.parse_args()


dir_path = os.path.dirname(os.path.realpath(__file__))
profile_path = dir_path + '/test_data/Achromobacter.tsv'
with open(profile_path, 'r') as f:
    profile = f.read()
    newick = module.MSTrees.backend(profile=profile)
    print(newick)