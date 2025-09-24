#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 22 22:23:24 2025

@author:ChronitonArray
"""

import pandas as pd
import numpy as np

data=pd.read_parquet("JusticeCanada_Consolidated_Acts_Regulations.parquet")

# %%
# Drop debug and init column
#

data=data.drop(columns=['debug','is_debug','is_init'])

# %%


#
# Blind conversion to categories for items with less than 30 different values
# size reduced from 2.7+G to 1.2G+
# 

# Convert common unhashable values (like lists/arrays) into hashable equivalents
def to_hashable(value):
    if isinstance(value, np.ndarray):
        # numpy arrays -> make them a tuple of their elements
        return tuple(value.tolist())
    if isinstance(value, (list, tuple)):
        # recursively convert inner elements
        return tuple(to_hashable(v) for v in value)
    if isinstance(value, dict):
        # convert dict to a sorted tuple of key, value pairs
        return tuple(sorted((k, to_hashable(v)) for k, v in value.items()))
    return value  # hashable type (numbers, strings, etc.)

def count_uniques_per_column(df):
    """
    Return a dictionary with the number of unique values for each column.
    Unhashable column values are converted to hashable representations first.
    """
    counts = {}
    for col in df.columns:
        # Transform to hashable values, then count uniques
        transformed = df[col].map(to_hashable)
        counts[col] = transformed.nunique(dropna=True)
    return counts

counts = count_uniques_per_column(data)
for col, c in counts.items():
    if c < 30:
        data[col] = data[col].astype('category')
        print(f'{col} modified to category   count:{c}')
    
# %%
    
data.to_parquet("JusticeCanada_Consolidated_Acts_Regulations__small.parquet")

