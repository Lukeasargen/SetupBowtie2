import numpy as np


genehits_nonread_headers = 7


def column_stats(table, columns):
    for n in columns:
        print( "\nColumn Stats : {}".format(n) )
        print( "Min={:.4f}. Max={:.4f}.".format(table[n].min(), table[n].max()) )
        print( "Median={:.4f}.".format(table[n].median()) )
        print( "Mean={:.3f}. Non-Zero Mean={:.3f}".format(table[n].mean(), table[table[n]!=0][n].mean()) )
        print( "Sum={:.4f}.".format(table[n].sum()) )
    print()


def read_fasta(filename, ret_name=False):
    # This line reads every single line from the fastas file and removes the endline character
    unedited = [line.rstrip('\n') for line in open(filename, 'r')]  # encoding="utf-8"
    # Combine all the lines into one long string
    # This is indexed from 1: because the first line is not part of the sequence
    fullseq = "".join(unedited[1:])
    if ret_name:
        # We get name from the first line, it's the first string before space but without the first character
        # It's wrapped as string just in case
        name = unedited[0].split()[0][1:]
        return fullseq, name

    return fullseq


def tamap_to_genehits(tamap, fasta_filename=None):
    """ Covert a TAmap table into a GeneHits table """
    tamap = tamap.copy()
    # Remove the intergenic regions
    genemap = tamap[tamap['Gene_ID'].notna()]
    # Get all the names by removing the suffix from the column names
    # and making a set (a set has no duplicates)
    # TAmap has 8 non-read headers
    map_names = set([ n for n in genemap.columns[8:] if n[-3:]=="sum" ])
    # Get other gene data into a genehits df
    grouped = genemap.groupby("Gene_ID", as_index=False)
    genehits = grouped.agg({"Start": "first", "End": 'first', "Direction": "first"})
    genehits["TA_Count"] = grouped["TA_Site"].count()["TA_Site"]
    genehits["Gene_Length"] = 1+genehits["End"] - genehits["Start"]
    # Compute GC content with the genome fasta file
    genehits["GC"] = None  # Blank
    if fasta_filename:
        full_seq = read_fasta(fasta_filename)
        for i, row in genehits.iterrows():
            seq = full_seq[row["Start"]:row["End"]+1].lower()
            gc = seq.count('g') + seq.count('c')
            genehits.loc[i, "GC"] = (gc)/len(seq)
    # Add the forward and reverse reads
    gene_hits_sum = grouped.sum()  # Get the number of hits per gene
    for name in map_names:
        genehits[name] = gene_hits_sum[name]
    return genehits


""" Normalization Operations """

def total_count_norm(genehits, columns=None, debug=False):
    """ Normalize tamap using the total reads."""
    temp = genehits.copy()
    if columns==None:
        columns = temp.columns[genehits_nonread_headers:]
    multiply_factor = {}
    for name in columns:
        multiply_factor.update({name: temp[name].sum()})
    max_total = max(multiply_factor.values())
    multiply_factor = {k:max_total/v for k,v in multiply_factor.items()}
    for k,v in multiply_factor.items():
        temp[k] = v*temp[k]
    if debug:
        print("\ntotal_count_norm")
        print("columns :", columns)
        print("max_total :", max_total)
        print("multiply_factor :", multiply_factor)
    return temp


def quantile_norm(genehits, q=0.5, columns=None, debug=False):
    """ Normalize tamap using the q'th quantile of the non-zero values."""
    temp = genehits.copy()
    if columns==None:
        columns = temp.columns[genehits_nonread_headers:]
    multiply_factor = {}
    for name in columns:
        multiply_factor.update({name: temp[temp[name]!=0][name].quantile(q=q)})
    max_total = max(multiply_factor.values())
    multiply_factor = {k:max_total/v for k,v in multiply_factor.items()}
    for k,v in multiply_factor.items():
        temp[k] = (max_total/v)*temp[k]
    if debug:
        print("\nquantile_norm q={}".format(q))
        print("max_total :", max_total)
        print("columns :", columns)
        print("multiply_factor :", multiply_factor)
    return temp


def gene_length_norm(genehits, columns=None, debug=False):
    """ Normalize genehits using the a length column. """
    temp = genehits.copy()
    if columns==None:
        columns = temp.columns[genehits_nonread_headers:]
    # Normalize by gene length
    lengths = 1+temp["End"]-temp["Start"]
    norm_length = lengths.mean()
    for name in columns:
        temp[name] = (norm_length/lengths)*temp[name]
    if debug:
        print("\ngene_length_norm")
        print("norm_length :", norm_length)
    return temp

