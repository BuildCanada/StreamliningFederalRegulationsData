#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 23 16:29:44 2025

@author: ChronitonArray
"""
import pandas as pd
import os, xmltodict, argparse
import pickle      #No currently used
from pathlib import Path
from typing import Union, Generator


# %%
#
# Find all xml in given path
# Path is static for now
#
def iter_files(root_path: Union[str, Path], file_extension='*.xml') -> Generator[Path, None, None]:
    """
    Generator file paths under root_path recursively.
    Accepts str or Path, expands user tilde, and yields only existing files.
    
    Parameters:
    - root_path: The root directory to start searching from. Can be relative or absolute.
    - file_extension: The type of file to process. file_extension='*.xml' for *.xml
    
    Yields:
    - Path objects for each found XML file (*.xml), in a lazy manner.
    """
    
    root = Path(root_path).expanduser().resolve(strict=False)
    
    if not root.exists():
        raise FileNotFoundError(f"Root path does not exist: {root}")
    
    for p in root.rglob(file_extension):
        if p.is_file():
            yield p

parser = argparse.ArgumentParser(
    description="Recursively yield XML files under a root directory."
)
parser.add_argument(
    "root",
    nargs="?",
    default="git/BuildCanada/StreamliningFederalRegulationsData/JusticeLawWebsite/formatted",
    help="Root path to search (relative to CWD or absolute). Defaults to current directory."
)
args = parser.parse_args()

# %%

#
# Parsing logic
# parse_layer() called by traverse(), and:
# - return a list of childrens (nested elements) as a list
# - update header of children accordingly (not stable)
# - return the current layer without the childtren (to becomes 1 row of data)

def init_sub_header(header, parent_key='', debug=''):  
    sub_header=header.copy()
    if len(header['current_fid']) > 0: 
        sub_header['parent_fid'] = header['current_fid']
    sub_header['current_fid'] = ''
    sub_header['parent_key'] = parent_key
    if header['is_debug']:    
        sub_header['debug'] = sub_header['debug'] + debug
    return sub_header

def reset_header(header):
    header['current_fid'] = ''
    header['other'] = []

def parse_layer (header, layer):
    sub_layers=[]
    to_pop=[]
    # reset header due to stray values
    header['other']=[]
    curr_fid=''
    
    # assign '@lims:fid' as curr_fid for consistency. likely droppable once stable
    if '@lims:fid' in layer: 
        curr_fid = layer['@lims:fid']
    header['current_fid']=curr_fid   
    
    # Fully initiating the header takes 2 cycles
    if not header['is_init']:
    
        # first key in document as doc_type. Expected resutl: 'Statute', 'Regulation', other
        if header['doc_type'] == '':
            header['doc_type']=list(layer)[0]
        
        # Set first fid as master_fid, parent_fid
        if len(curr_fid) > 0:
            header['master_fid'] = header['parent_fid'] = curr_fid
            # init completed
            header['is_init'] = True
            # print('header init: true')
    
    # If current layer is a dictionary (most common)
    if isinstance(layer, dict):
        if header['is_debug']:
            header['debug'] = '"layer:dict" '
            # header['debug'] = header['debug'] + '"layer:dict" '
        for k,v in layer.items():            
            if isinstance(v,str):
                # Do nothing, keep
                pass
            
            elif isinstance(v, dict):
                # start from a fresh copy of header
                sub_header=init_sub_header(header, parent_key=k, debug='dict-dict ')
                to_pop.append(k)
                sub_layers.append([sub_header, v])
            elif isinstance(v, list):
                sub_header=init_sub_header(header, parent_key=k, debug='dict-list ')
                for item in v:
                    sub_layers.append([sub_header, v])
                    
                # $emove entire list from layer
                to_pop.append(k)
            elif v == None:
                # suspect xmltodict parsing issue
                to_pop.append(k)
            else: 
                print('Unexpected type wile parsing dictionary:')
                print(f'Header value: {header}')
                print(f'Layer value: {layer}')
                print('------------------------')
        # remove parsed entry from layer
        # must be done outside the loop
        for k in to_pop:
            layer.pop(k)
            
    # If current layer is a list (should be rare with this algorithm)
    elif isinstance(layer, list):
        
        # if list then no key or anything to pass on.
        # apply current header to every entry
        # create copy for ease of debugging
        sub_header=header.copy()
        if header['is_debug']:
            sub_header['debug'] = '"layer:list" '
            # sub_header['debug'] = sub_header['debug'] + '"layer:list" '
        for index,item in enumerate(layer):
            if isinstance(item, dict):
                if header['is_debug']:
                    sub_header['debug'] = sub_header['debug'] + 'list-dict '
                sub_layers.append([sub_header, item])
                
            elif isinstance(item, list):
                if header['is_debug']:
                    sub_header['debug'] = sub_header['debug'] + 'list-list '
                for subitem in item:
                    sub_layers.append(sub_header, item)
            elif isinstance(item, str):
                if header['is_debug']:
                    sub_header['debug'] = sub_header['debug'] + 'list-str '
                header['other'].append(item)
            elif item == None:
                # suspect xmltodict parsing issue
                pass
            # remove entry from layer - will likely return an emtpy table
        
        # drop entire list - any data in list saved in header['other']
        # if header['other'] is empty => layer discarded
        layer=dict()
            
    else: 
        print('Unexpected type wile parsing layer, not a list or dictionary:')
        print(f'Header value: {header}')
        print(f'Layer value: {layer}')
        print('------------------------')
    
    return header, layer, sub_layers

# %%

#
# Parsing logic
# traverse() calls parse_layer() and receive the current layer, and the list of sub_layers 
# then calls parse_layer() on each sub_layers
#
# Customs fields are contained in 'header'
# later joined with its respective layer to form a row
#

def traverse (xml, doc_name, key_set):
    extracted_layer = list()
    to_process = list()
    new_to_DataFrame = list()
    # Some extra field to carry over, when 1 layer is a list with no metadata
    header={
        'doc_name' : doc_name,
        'doc_type': '',          # First 'Key' of document - e..g 'Statute', 'Regulation'
        'master_fid' :'',        # First fid of the document
        'parent_fid' : '',        # fid of the parent layer - 1st layer == master_fid == 
        'current_fid' : '',     # droppable; to simplify logic
        'parent_key' : '',        # Likely dropable; to keep relationship with nested list - 1st layer == doc_type
        'is_init' : False,  # Dropable, for internal logic
        # Placeolder for stray items
        'other' : [],
        # debug field - Drop once stable
        'debug': '',
        'is_debug': False
        }
    
    # --------------------- 1st layer extract ------------------------------------------------------------------------
    
    # core function call
    header, extracted_layer, sub_layers = parse_layer(header, xml) 
    
    # merge header and extracted layer for later conversion to DataFrame
    if len(header['other']) > 0 or len(extracted_layer) > 0:    
        new_to_DataFrame.append({**header, **extracted_layer})
    
    for header, layer in sub_layers:
        to_process.append([header, layer])
    
    # Clearing memory
    extracted_layer.clear()
    sub_layers.clear()

    # ---------------------- Layer parsing -------------------------------------------------------------------------
    while len(to_process) > 0:
        
        # Main function call
        header, layer = to_process.pop()
        header, extracted_layer, sub_layers = parse_layer(header, layer) 
        
        # merge header and extracted layer for later conversion to DataFrame
        if len(header['other']) > 0 or len(extracted_layer) > 0:    
            new_to_DataFrame.append({**header, **extracted_layer})
        
        for header, layer in sub_layers: 
            to_process.append([header, layer])
        
        # clearning memory
        extracted_layer.clear()
        sub_layers.clear()
        
    # Update list of keys for DataFrame generation
    for item in new_to_DataFrame: 
        key_set = key_set.union({*item})

    return new_to_DataFrame, key_set

# %%

#
# MAIN
# load an xml + calls traverse()
# receive a list of dictionary (rows)
# receive a key_set (sets of columns) for buiding the DataFrame
#

def main():
    
    # Will save as Parquet. Otherwise will save as a pickled list of dictionary
    # No chunking with parquet
    is_parquet=True
    
    # Set to True to limit how many files are processed
    limit_count=False
    max_count=10
    
    # start of counter
    count=0
    # limit the size  of table when pickling
    # check only after parsing each file, final size may vary
    enable_chunks=False
    chunk_size=1E5
    
    chunk_list= new_chunk = list()
    
    file_save_count=0
    key_set=set()       # Set of all key values - for DataFrame generation with chunked list
    
    for xml_file in iter_files(args.root, "*.xml"):
        count += 1
        # print(f'processiong file: {xml_file}')
    
        doc_name=os.path.basename(xml_file)
        
        if not limit_count or count <= max_count:
            with open(xml_file, "rb") as file:
                doc=xmltodict.parse(file, dict_constructor=dict)
                
            new_chunk, key_set = traverse(doc, doc_name, key_set)
            chunk_list += new_chunk
            # print('at list_chunk size check')
            if enable_chunks and len(chunk_list) > chunk_size and not is_parquet :
                file_save_count += 1
                save_as="JusticeCanada_Consolidated_list_chunk_"+str(file_save_count)+".pkl" 
                print(f'Saving {save_as}. Lenght of list: {len(chunk_list)}')
                with open(save_as, "wb") as out_file:
                    pickle.dump(chunk_list, out_file)
                chunk_list.clear()
    
    
    if enable_chunks and not is_parquet:
        # Final save for partial chunk
        if len(chunk_list) > 0: 
            file_save_count += 1
            save_as="JusticeCanada_Consolidated_list_chunk_"+str(file_save_count)+".pkl" 
            print(f'Saving {save_as}. Lenght of list: {len(chunk_list)}')
            with open(save_as, "wb") as out_file:
                pickle.dump(chunk_list, out_file) 
    elif enable_chunks:
        # save as 1 chunk
        save_as="JusticeCanada_Consolidated_Acts_Regulations.pkl" 
        print(f'Saving {save_as}. Lenght of list: {len(chunk_list)}')
        with open(save_as, "wb") as out_file:
            pickle.dump(chunk_list, out_file) 
    else:
        # save to parquet
        save_as="JusticeCanada_Consolidated_Acts_Regulations.parquet" 
        print(f'Saving {save_as}. Lenght of list: {len(chunk_list)}')
        with open(save_as, "wb") as out_file:
            pd.DataFrame(chunk_list, columns=list(key_set)).to_parquet(out_file, engine="pyarrow")
    # save key_set (list of columns)
    with open("key_set.pkl",'wb') as f:
        pickle.dump(key_set, f)

# %%

if __name__ == "__main__":
    main()
else:
    main()
    
# %%

#
# REFERENCE
# list of columns for DataFrame
#


# key_set={
#   '#text',
#   '@align',
#   '@bilingual',
#   '@bill-origin',
#   '@bill-type',
#   '@bottommarginspacing',
#   '@change',
#   '@char',
#   '@charoff',
#   '@colname',
#   '@colnum',
#   '@cols',
#   '@colsep',
#   '@colwidth',
#   '@date-time',
#   '@enddate',
#   '@first-line-indent',
#   '@float',
#   '@font-family',
#   '@fontsize',
#   '@fontstyle',
#   '@format-ref',
#   '@frame',
#   '@gazette-part',
#   '@generate-in-text',
#   '@group-style',
#   '@hasPreviousVersion',
#   '@height',
#   '@hyphenation',
#   '@id',
#   '@idref',
#   '@in-force',
#   '@include-in-TableOfProvisions',
#   '@indent-level',
#   '@isURL',
#   '@justification',
#   '@keep-together',
#   '@keep-with-next',
#   '@keep-with-previous',
#   '@label-id',
#   '@language-align',
#   '@lawid',
#   '@leader',
#   '@length',
#   '@level',
#   '@lims:current-date',
#   '@lims:enactId',
#   '@lims:enacted-date',
#   '@lims:fid',
#   '@lims:id',
#   '@lims:inforce-end-date',
#   '@lims:inforce-start-date',
#   '@lims:lastAmendedDate',
#   '@lims:pit-date',
#   '@link',
#   '@list-direction',
#   '@list-item',
#   '@mathsize',
#   '@maxsize',
#   '@morerows',
#   '@nameend',
#   '@namest',
#   '@official',
#   '@orientation',
#   '@overflow',
#   '@pagebreakafter',
#   '@placement',
#   '@pointsize',
#   '@position',
#   '@reference-level',
#   '@reference-type',
#   '@regulation-type',
#   '@revised-statute',
#   '@rowbreak',
#   '@rowheader',
#   '@rowsep',
#   '@salutation',
#   '@source',
#   '@spanlanguages',
#   '@spanmarginalnotecol',
#   '@stage',
#   '@startdate',
#   '@status',
#   '@style',
#   '@subsequent-line-indent',
#   '@svc',
#   '@target',
#   '@th-headers',
#   '@th-id',
#   '@topdouble',
#   '@topmarginspacing',
#   '@type',
#   '@valign',
#   '@width',
#   '@xml:lang',
#   '@xml:space',
#   '@xmlns:lims',
#   '@xmlns:xlink',
#   'AlternateText',
#   'AmendmentCitation',
#   'AmendmentDate',
#   'AnnualStatuteNumber',
#   'Base',
#   'BilingualItemEn',
#   'BilingualItemFr',
#   'BillNumber',
#   'BillRefNumber',
#   'Caption',
#   'Citation',
#   'DD',
#   'Date',
#   'DefinedTermEn',
#   'DefinedTermFr',
#   'DefinitionEnOnly',
#   'DefinitionRef',
#   'Del',
#   'Denominator',
#   'Emphasis',
#   'FootnoteRef',
#   'FormulaConnector',
#   'FormulaTerm',
#   'FormulaText',
#   'HistoricalNote',
#   'HistoricalNoteSubItem',
#   'IBR',
#   'Ins',
#   'InstrumentNumber',
#   'Keep',
#   'Label',
#   'LongTitle',
#   'MM',
#   'MarginalNote',
#   'Monarch',
#   'Note',
#   'Number',
#   'Numerator',
#   'Oath',
#   'OrderNumber',
#   'OriginatingRef',
#   'OtherAuthority',
#   'RegulationMaker',
#   'Repealed',
#   'Reserved',
#   'Separator',
#   'Session',
#   'SignatureLine',
#   'SignatureName',
#   'SignatureTitle',
#   'StatuteYear',
#   'Sub',
#   'Subscript',
#   'Sup',
#   'Superscript',
#   'Text',
#   'TitleText',
#   'XRefInternal',
#   'YYYY',
#   'Year-s',
#   'current_fid',
#   'debug',
#   'doc_name',
#   'doc_type',
#   'entry',
#   'is_debug',
#   'is_init',
#   'master_fid',
#   'mi',
#   'mn',
#   'mo',
#   'mtext',
#   'other',
#   'parent_fid',
#   'parent_key',
#   'title',
#  }
