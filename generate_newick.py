import os
import argparse
from sys import stdout

from grapetree import module

parser = argparse.ArgumentParser(description='Generate a Newick file from a file containing allele profiles.')
parser.add_argument('profile_file', help='Full path and filename for the profile file')
args = parser.parse_args()

with open(args.profile_file, 'r') as f:
    profile = f.read()
    newick = module.MSTrees.backend(profile=profile)
    stdout.write(newick)