# -*- coding: utf-8 -*-

import glob
import os
import numpy as np

METADATA_FIELDS = ['COMMENT','NAME','ANNOTATION','SHORT_ANNOTATION']

def load_db(db_list,db_path):
    # loads the dbs listed in the list
    # items in the list should be folder names in the dirctory indicated by db_path
    filenames = []
    for dir_name in db_list:
        glob_path = os.path.join(db_path,dir_name,'*.m2m')
        print "Looking in {}".format(glob_path)
        new_filenames = glob.glob(glob_path)
        filenames += new_filenames
        print "\t Found {}".format(len(new_filenames))

    print "Found total of {} motif files".format(len(filenames))

    metadata = {}
    spectra = {}

    for filename in filenames:
        motif_name = os.path.split(filename)[-1]
        spectra[motif_name],metadata[motif_name] = parse_m2m(filename)

    return spectra,metadata

def parse_m2m(filename):
    metadata = {}
    spectrum = {}
    with open(filename,'r') as f:
        for line in f:
            if line.startswith('#'):
                # it's some metadata
                tokens = line.split()
                key = tokens[0][1:]
                if key in METADATA_FIELDS:
                    new_value = " ".join(tokens[1:])
                    if not key in metadata:
                        metadata[key] = new_value
                    else:
                        # is it a list already?
                        current_value = metadata[key]
                        if isinstance(current_value,list):
                            metadata[key].append(new_value)
                        else:
                            metadata[key] = [current_value].append(new_value)
                else:
                    print "Found unknown key ({}) in {}".format(key,filename)
            elif len(line)>0:
                mz,intensity = line.split(',')
                spectrum[mz] = float(intensity)
    return spectrum,metadata


class MotifFilter(object):
    def __init__(self,spectra,metadata,threshold = 0.95):
        self.input_spectra = spectra
        self.input_metadata = metadata
        self.threshold = threshold

    def filter(self):
        # Greedy filtering
        # Loops through the spectra and for each one computes its similarity with 
        # the remaining. Any that exceed the threshold are merged
        # Merging invovles the latter one and puts it into the metadata of the 
        # original so we can always check back. 
        spec_names = sorted(self.input_metadata.keys())
        final_spec_list = []
        while len(spec_names) > 0:
            current_spec = spec_names[0]
            final_spec_list.append(current_spec)
            del spec_names[0]
            merge_list = []
            for spec in spec_names:
                sim = self.compute_similarity(current_spec,spec)
                if sim >= self.threshold:
                    merge_list.append((spec,sim))
            if len(merge_list) > 0:
                merge_data = []
                for spec,sim in merge_list:
                    print "Merging: {} and {} ({})".format(current_spec,spec,sim)
                    # chuck the merged motif into metadata so that we can find it later
                    merge_data.append((spec,self.input_spectra[spec],self.input_metadata[spec],sim))
                    pos = spec_names.index(spec)
                    del spec_names[pos]
                self.input_metadata[current_spec]['merged'] = merge_data
        
        output_spectra = {}
        output_metadata = {}
        for spec in final_spec_list:
            output_spectra[spec] = self.input_spectra[spec]
            output_metadata[spec] = self.input_metadata[spec]
        return output_spectra,output_metadata

    def compute_similarity(self,k,k2):
        # compute the cosine similarity of the two spectra
        prod = 0
        i1 = 0
        for mz,intensity in self.input_spectra[k].items():
            i1 += intensity**2
            for mz2,intensity2 in self.input_spectra[k2].items():
                if mz == mz2:
                    prod += intensity * intensity2
        i2 = sum([i**2 for i in self.input_spectra[k2].values()])
        return prod/(np.sqrt(i1)*np.sqrt(i2))
