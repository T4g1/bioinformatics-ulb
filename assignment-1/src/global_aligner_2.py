import numpy as np
from Bio import SeqIO, pairwise2
from Bio.SubsMat import MatrixInfo
import utils
import random
import pandas as pd

import numpy as np


aminoacid_names = "ARNDCEQGHILKMFPSTWYV"
print("Number of aminoacids:", len(aminoacid_names))

gap_penalty = -1

min_string_size = 20
max_string_size = 70


def sub_matrices_distance(c1, c2, matrix=MatrixInfo.pam120):
    """
    Get the substitution score for c1 and c2 
    according to the provided substitution matrix.
    
    Parameters
    ----------
    c1, c2: char
    
    matrix: Bio.SubsMat.MatrixInfo.available_matrix, optional
        The substitution matrix to be used, among the ones available in Bio.SubsMat.MatrixInfo
        
    Returns 
    ----------
    int  
        the score for substituting c1 with c2.
    """
    return matrix[(c1, c2)] if (c1, c2) in matrix else matrix[(c2, c1)]
    

def global_aligner_2(s1, s2, gap_penalty = -1, edit_function=sub_matrices_distance, matrix=MatrixInfo.pam120, semiglobal=False):
    """
    Compute the global alignment between 2 aminoacid sequences "s1" and "s2".
    
    Parameters 
    ----------
    s1, s2: string
        The two input aminoacid sequences on which the edit distance is computed.
        
    gap_penalty: int, optional
        The penalty factor assigned to matching an aminoacid to a gap character.
        It should be a NEGATIVE integer.
        
    edit_function: function, optional
        The function that is used to compute the cost of an aminoacid subtitution.
        
    matrix: Bio.SubsMat.MatrixInfo.available_matrix, optional
        The substitution matrix to be used, among the ones available in Bio.SubsMat.MatrixInfo.
        It is used by edit_function, if needed.
        
    semiglobal: bool
        Set to false to penalize the sequences for not being aligned at the start.
        If true, don't penalize gaps at the beginning of the alignment.

    Returns 
    ----------
    int
        The edit distance between s1 and s2
    """
    n_row= len(s1) + 1
    n_col = len(s2) + 1
    edit_matrix = np.zeros((n_row, n_col))
    backtrack_matrix = pd.DataFrame("", index=np.arange(n_row), columns=np.arange(n_col))
                                   
    for i in range(n_row):
        edit_matrix[i, 0] = i * (0 if semiglobal else gap_penalty)
        backtrack_matrix.set_value(i, 0, "V")
                        
    for j in range(n_col):
        edit_matrix[0, j] = j * (0 if semiglobal else gap_penalty)
        backtrack_matrix.set_value(0, j, "H")
    # Set the first cell of the backtrack matrix to "X", as an end-marker.
    backtrack_matrix.set_value(0, 0, "X")
                       
    for i in range(1, n_row):
        for j in range(1, n_col):
            s1_gap = edit_matrix[i - 1, j] + gap_penalty
            s2_gap = edit_matrix[i, j - 1] + gap_penalty
            mut = edit_matrix[i - 1, j - 1] + edit_function(s1[i - 1], s2[j - 1], matrix=matrix)
            edit_matrix[i, j] = max(s1_gap, s2_gap, mut)

            # Check which movements are the best, return it as a list where 1 = max of the list.
            m_list = [s1_gap, s2_gap, mut]
            mov = np.array(["V", "H", "D"])
            
            # Write in the matrix the movement that lead to that cell, as a string.
            # e.g. "HV" means that horizontal and vertical movements were the best. 
            backtrack_matrix.set_value(i, j, "".join(mov[np.argwhere(m_list == np.max(m_list)).flatten()]))
            
    return [edit_matrix[len(s1), len(s2)], edit_matrix, backtrack_matrix]
    

def backtrack_sequence(s1, s2, backtrack_matrix):
    i = len(s1)
    j = len(s2) 
    aligned_s1 = ""
    aligned_s2 = ""    
    match_sequence = ""

    over = False
    
    while not over:
        for mov in backtrack_matrix.iloc[i, j][0]:
            if mov == "V":
                aligned_s1 = s1[i - 1] + aligned_s1
                aligned_s2 = "-" + aligned_s2
                match_sequence = " " + match_sequence
                i -= 1
            elif mov == "H":
                aligned_s1 = "-" + aligned_s1
                aligned_s2 = s2[j - 1] + aligned_s2
                match_sequence = " " + match_sequence
                j -= 1
            elif mov == "D":
                aligned_s1 = s1[i - 1] + aligned_s1
                aligned_s2 = s2[j - 1] + aligned_s2
                match_sequence = (":" if s1[i - 1] == s2[j - 1] else ".") + match_sequence
                i -= 1
                j -= 1       
            elif mov == "X":
                over = True
            else:
                 raise ValueError("val={0} isn't a valid movement!".format(mov))

    return [aligned_s1, aligned_s2, match_sequence]
                
     
def backtrack_sequence_rec(s1, s2, backtrack_matrix):
    i = len(s1)
    j = len(s2) 

    align = utils.Alignment()
    align_list = [align]
    for mov in backtrack_matrix.iloc[i, j]:
        if mov == "V":        
            align_temp = backtrack_sequence_rec(s1[:i-1], s2[:j], backtrack_matrix.iloc[:i, :j+1]) \
                                           + utils.Alignment(s1[i-1], "-", " ") 
            align_list = [align_temp + align for align in align_list]
            i -= 1
        elif mov == "H":
            align_temp = backtrack_sequence_rec(s1[:i], s2[:j-1], backtrack_matrix.iloc[:i+1, :j]) \
                                           + utils.Alignment("-", s2[j-1], " ") 
            align_list = [align_temp + align for align in align_list]
            j -= 1
        elif mov == "D":
            align_temp = backtrack_sequence_rec(s1[:i-1], s2[:j-1], backtrack_matrix.iloc[:i, :j]) \
                                           + utils.Alignment(s1[i-1], s2[j-1],  (":" if s1[i-1] == s2[j-1] else "."))                                  
            align_list = [align_temp + align for align in align_list]
            i -= 1
            j -= 1             
        elif mov == "X":
            return align
        else:
            raise ValueError("val={0} isn't a valid movement!".format(mov))

    return align       
     



##########################################
# TEST ###################################
##########################################



             
# Load the sequences and test their edit distance
#for i, seq_record_i in enumerate(SeqIO.parse("../data/WW-sequence.fasta", "fasta")):
#   for j, seq_record_j in enumerate(SeqIO.parse("../data/WW-sequence.fasta", "fasta")):
#       if i > j :
#            print("Comparing:\n\t", seq_record_i.id, "-- length:", len(seq_record_i))
#            print("\t", seq_record_j.id, "-- length:", len(seq_record_j))
#            [score, edit_matrix, backtrack_matrix] = global_aligner_2(seq_record_i.seq,  seq_record_j.seq, gap_penalty=-1, matrix=MatrixInfo.blosum62)
#            align = backtrack_sequence_rec(seq_record_i.seq, seq_record_j.seq, backtrack_matrix)
#            s1_al = align.s1
#            s2_al = align.s2
#            mat = align.match
#            print(s1_al)
#            print(mat)
#            print(s2_al)
#            print("MY ALIGNER:", score)
#            print("BIOPYTHON ALIGNER", pairwise2.align.globaldx(seq_record_i.seq, seq_record_j.seq, MatrixInfo.blosum62, score_only = True))
#            print("\n")




s1 = "THISLINE"
s2 = "ISALIGNED"
[score, edit_matrix, backtrack_matrix] = global_aligner_2(s1, s2, gap_penalty=-4, matrix=MatrixInfo.blosum62, semiglobal=True)

print(edit_matrix)
print(backtrack_matrix)

edit_frame = pd.DataFrame(edit_matrix)
edit_frame.index = list(" " + s1)
edit_frame.columns = list(" " + s2)

align = backtrack_sequence_rec(s1, s2, backtrack_matrix)
s1_al = align.s1
s2_al = align.s2
mat = align.match
print(s1_al)
print(mat)
print(s2_al)
