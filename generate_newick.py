import os

from grapetree import module

if __name__ == '__main__':
    dir_path = os.path.dirname(os.path.realpath(__file__))
    profile_path = dir_path + '/test_data/Achromobacter.tsv'
    with open(profile_path, 'r') as f:
        profile = f.read()
        newick = module.MSTrees.backend(profile=profile)
        print(newick)