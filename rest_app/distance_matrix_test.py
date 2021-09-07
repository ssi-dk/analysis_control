from datetime import datetime
import yaml
from datetime import datetime

import pandas as pd


with open('config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

print(f"Application starting at {datetime.now().time()}")
distance_matrices = dict()
for k, v in config['distance_matrices'].items():
    print(f"Loading distance matrix for {k}...")
    print(f"File location: {v['location']}")
    distance_matrices[k] = pd.read_csv(v['location'], sep=' ', index_col=0, header=None)

matrix: pd.DataFrame = distance_matrices['Salmonella_enterica']

for y in matrix.iterrows():
    x = y[1]
    for v in x.iteritems():
        print(v)
    print()

print("OK, but there's a much better way to find a certain row in the dataframe.")
print("Now, I want Pandas to show me the row where index is '2010S00330':")
my_row = matrix.loc[ '2010S00330' , : ]
print(my_row)