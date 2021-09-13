import argparse
from random import random

from faker import Faker

parser = argparse.ArgumentParser()
parser.add_argument('size')
args = parser.parse_args()
size = int(args.size)

fake = Faker()
Faker.seed(0)

filename = f'fake_dm_{args.size}.tsv'

# Prepare file with random sequence numbers.
with open(filename, 'w') as f:
    for y in range(size):
        sequence_name = fake.bothify(text='####S#####') + ' '
        f.write(sequence_name)
        for x in range(size):
            f.write(str(random() * 10) + ' ')
        f.write('\n')
