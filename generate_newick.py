from grapetree import module

if __name__ == '__main__':
    with open('Grapetree_Agona.profile', 'r') as f:
        profile = f.read()
        newick = module.MSTrees.backend(profile=profile)
        print(newick)