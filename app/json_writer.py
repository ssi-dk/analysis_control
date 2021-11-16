#!/usr/bin/env python3

import datetime
import sys
import os
from time import strftime, localtime
import pandas as pd
import json
import csv
import numpy as np
import argparse
import yaml

# GOAL: export allele profiles to json
# Components
# * sample information
# * allele statistics
# * allele profile (hashed; or full allele sequence)
# * detailed allele properties: source of error, 


# input
# Details on contig info
#/home/carlus/BfR/Projects/Pipeline_test/chewieSnake/cgmlst/GMI-17-001-DNA/results_contigsInfo.tsv
# link with contig depth

# allele details unhashed
# "/home/carlus/BfR/Projects/Pipeline_test/chewieSnake/cgmlst/GMI-17-001-DNA/results_alleles.tsv"

# paralogs:
#/home/carlus/BfR/Projects/Pipeline_test/chewieSnake/cgmlst/GMI-17-001-DNA/RepeatedLoci.txt

# functions
def convert_np2number(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime.datetime):
        return obj.__str__()


def compute_locus_stats(stats):
    # ' function that computes allele quality metrics from chewBBaca
    loci_found = stats['EXC'] + stats['INF']
    loci_missing = stats['LNF'] + stats['PLOT'] + stats['NIPH'] + stats['ALM'] + stats['ASM']
    loci_total = loci_found + loci_missing
    loci_missing_fraction = loci_missing / loci_total
    loci_missing_fraction

    loci_info = {'loci_found': loci_found.iloc[0],
                 'loci_missing': loci_missing.iloc[0],
                 'loci_total': loci_total.iloc[0],
                 'loci_missing_fraction': loci_missing_fraction.iloc[0],
                 }
    return (loci_info)



def collect_allele_profile(allele_profile_file):
    # load allele profile of single sample
    # profile = pd.read_csv(allele_profile_file, index_col="FILE", sep="\t") # strict index column FILE
    profile = pd.read_csv(allele_profile_file, index_col=0, sep="\t")

    # check that only single sample
    if len(profile.index) > 1:
        print("Only profile files containing a single sample (single profile row) are permitted.")
        sys.exit(1)

    # convert allele profiles to dictionary
    #allele_numbers = profile.to_dict('list') # writes values as list
    allele_numbers = profile.to_dict('records')[0]

    return(allele_numbers)

def collect_allele_stats(allele_stats_file):
    # load allele stats
    stats = pd.read_csv(allele_stats_file, index_col="sample", sep="\t")
    # allele_stats = stats.to_dict('list') # returns values as list
    allele_stats = stats.to_dict(orient='records')[
        0]  # returns values as integers, however entire dictionary is list; [0] casts to dict
    # stats.to_dict(orient='index') # returns nested dict

    # update allele stats with derived locus stats
    allele_stats.update(compute_locus_stats(stats))

    return(allele_stats)


def collect_sample_info(args, parameter_format):
    # make a sample description

    # profile time stamp
    timestamp = strftime("%Y-%m-%d", localtime(os.path.getmtime(args.allele_profile)))
    # sample name
    sample_name3 = args.sample_name
    profile = pd.read_csv(args.allele_profile, index_col="#FILE", sep="\t")
    sample_name1 = ''.join(profile.index).strip('.fasta')  # name of fasta file
    sample_name2 = os.path.basename(os.path.dirname(args.allele_profile))  # name of directory
    # minimal description
    sample_description = {'file': args.allele_profile, 'sample_name': sample_name1, 'sample_name2': sample_name2, 'sample_name3': sample_name3,
                          'file_timestamp': timestamp}

    if parameter_format == "json":
        # load json to dictionary
        with open(args.pipeline_metadata, "r") as infile:
            pipeline_metadata = json.load(infile)

        with open(args.scheme_information, "r") as infile:
            scheme_information = json.load(infile)
    else:
        # load yaml to dictionary
        with open(args.scheme_information, "r") as handle:
            scheme_information = yaml.load(handle, Loader=yaml.FullLoader)
        with open(args.pipeline_metadata, "r") as handle:
            pipeline_metadata = yaml.load(handle, Loader=yaml.FullLoader)



    technical_metadata = {'sample_description': sample_description, 'pipeline_metadata': pipeline_metadata,
                          'scheme_information': scheme_information}

    return(technical_metadata)

#def combine_json(allele_profile, allele_stats, sample_info, args):
 # not needed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--allele_profile', help='Path to hashed allele profile for a single sample (tsv)', required=True, type=os.path.abspath)
    parser.add_argument('-s', '--allele_stats', help='Path to allele stats for a single sample (tsv)', required=True, type=os.path.abspath)
    #parser.add_argument('-o', '--outdir', help='Output dir', required=False, default='/', type=os.path.abspath)
    parser.add_argument('-o', '--outfile', help='Output file', required=True, type=os.path.abspath)

    parser.add_argument('--pipeline_metadata', help='Path to predefined pipeline metadata (yaml)', required=True, type=os.path.abspath)
    parser.add_argument('--scheme_information', help='Path to predefined scheme information (yaml)', required=True, type=os.path.abspath)
    parser.add_argument('--json_input', help='Input pipeline metadata and scheme information are in json instead of yaml format', default=False, action='store_true',  required=False)

    # sample info
    parser.add_argument('--sample_name', help='Sample name', default = "NA", required=False)
    #parser.add_argument('--analysis_date', help='date of analysis', default = "NA", required=False)
    #parser.add_argument('--assembler', help='assembler', default = "NA", required=False)
    #parser.add_argument('--allele_caller', help='Allele caller', default = "NA", required=False)
    #parser.add_argument('--scheme', help='Scheme', default = "NA", required=False)

    #parser.add_argument('--yaml', help='Output yaml instead of json', default=False, action='store_true',  required=False)
    args = parser.parse_args()

    # convert allele profile tsv into dictionary
    allele_numbers = collect_allele_profile(args.allele_profile)

    # convert allele stats tsv into dictionary
    allele_stats = collect_allele_stats(args.allele_stats)
    
    # combine sample metadata into dictionary
    if args.json_input:
        parameter_format = "json"
    else:
        parameter_format = "yaml"
    technical_metadata = collect_sample_info(args, parameter_format)

    # write json to file
    metadict = {'technical_metadata': technical_metadata, 'allele_numbers': allele_numbers,
                'allele_stats': allele_stats}

    # convert to json string
    metadict_json = json.dumps(metadict, default=convert_np2number)

    # define outname
    # if args.outdir != "/":
        # outdir = args.outdir
        # print("outdir specified as " + outdir)
    # else:
        # outdir = os.path.dirname(args.allele_profile)
        # print("outdir inferred from file " + outdir)

    if args.sample_name != "NA":
        sample_name = args.sample_name
        print("Sample name provided")
    else:
        sample_name = technical_metadata['sample_description']['sample_name']
        print("Sample name inferred from technical metadata")


    # infer output name from sample name
#    filename_out = sample_name + '.alleles' + '.json'
#    allele_profile_json = os.path.join(outdir, filename_out)
    allele_profile_json = args.outfile


    print("Writing output to:")
    print(allele_profile_json)

    if os.path.exists (allele_profile_json):
        print("WARNING: outfile " + allele_profile_json + "exists and will be overwritten")


    # save json to file
    with open(allele_profile_json, "w") as file:
        file.write(metadict_json)


    print("Thank you for using the allele to json converter")

if __name__ == '__main__':
    main()

# sample_info
# name
# name, hashed
# analysis date
# sender
# contact
# assembler
# e.g. shovill
# assembler_version: software version
# assembler_parameters: spades, kmers, extra, defaults
# trimming
# e.g. fastp
# trimming parameters: minimum length, quality
# sequencing instrument
# sequencing kit
# average depth
# allele caller
# e.g.
# allele_caller version
# allele_caller
# scheme name
# scheme genes
# scheme data
# scheme source
# sample metadata

